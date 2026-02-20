#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Topstep Combine Evaluation — MNQ EMA Crossover Strategy
=========================================================

Topstep Rules:
  Account size:       $50,000
  Max contracts:      50 MNQ micros
  Profit target:      $3,000  (trailing drawdown freezes when reached)
  Max loss limit:     $2,000  (trailing drawdown from high-water mark)
  Daily loss limit:   None
  Consistency rule:   No single day > 50% of total net profit
  Holding timeline:   No positions held past 4:00 PM ET
  Fees Structure:     $0.74 per contract on entry, no slippage

Strategy:
  - EMA50 crosses above EMA200 → long 3 MNQ contracts
  - EMA50 crosses below EMA200 → short 3 MNQ contracts
  - Each trade risks $150 with a $150 profit target
  - Bracket orders (stop-loss + take-profit) placed at entry

MNQ specs:
  tick_size  = 0.25  (quarter NQ index point)
  tick_value = $0.50 per tick per contract
  1 NQ point = 4 ticks = $2.00 per contract

Risk/reward per trade (3 contracts):
  $150 risk   = $50/contract / $2 per point = 25 NQ points
  $150 target = $50/contract / $2 per point = 25 NQ points

Expected CSV format (Databento-style):
  ts_event,Open,High,Low,Close,Volume
  2021-01-26 19:00:00-05:00,13560.25,13567.0,13553.5,13562.25,731
  ...
  The ts_event column must be timezone-aware (offset included).
  All sessions (Asia, London, New York) are included by default.

Usage:
  python topstep-mnq.py --data /path/to/mnq_5min.csv
  python topstep-mnq.py --data /path/to/mnq_5min.csv --printlog
  python topstep-mnq.py --data /path/to/mnq_5min.csv --fromdate 2024-01-01 --todate 2024-06-30
  python topstep-mnq.py --data /path/to/mnq_5min.csv --rth-only   # RTH only (09:30-16:00 ET)
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import datetime
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import backtrader as bt
from backtrader.commissions.futures import MNQFuturesCommInfo
from backtrader.analyzers.propfirm_drawdown import PropFirmDrawDown
from backtrader.analyzers.consistency import ConsistencyAnalyzer
from backtrader.strategies.position_closer import EODPositionCloserMixin
from backtrader.sizers.max_contracts import MaxContractsSizer


# MNQ: tick_value=$0.50, tick_size=0.25 → $2.00 per NQ index point per contract
_MNQ_COMM = MNQFuturesCommInfo()
MNQ_POINT_VALUE = _MNQ_COMM.p.tick_value / _MNQ_COMM.p.tick_size  # 2.0


# ── Data loading ─────────────────────────────────────────────────────────────

def load_mnq_csv(filepath, fromdate=None, todate=None, rth_only=True):
    """
    Load a Databento-style MNQ CSV file and return a backtrader PandasData feed.

    Expected columns: ts_event, Open, High, Low, Close, Volume
    ts_event format:  2021-01-26 19:00:00-05:00  (timezone-aware, ET offset)

    The timezone offset is stripped after converting to America/New_York so
    DST transitions (EST=-05:00 / EDT=-04:00) are handled correctly.

    When rth_only=True (default), only bars from 09:30 to 15:55 ET are kept.
    This matches Regular Trading Hours and ensures the EOD-close timer at
    16:00 fires after the last RTH bar.
    """
    df = pd.read_csv(filepath)

    # Parse tz-aware timestamps → convert to ET → strip tz to get naive ET datetimes
    # tz_convert handles DST: -05:00 (EST) and -04:00 (EDT) both map correctly
    df['datetime'] = (
        pd.to_datetime(df['ts_event'], utc=True)
        .dt.tz_convert('America/New_York')
        .dt.tz_localize(None)
    )

    # Standardize column names to lowercase for backtrader
    df = df.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low':  'low',
        'Close': 'close',
        'Volume': 'volume',
    })

    df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
    df = df.set_index('datetime')
    df = df.sort_index()

    # Optional date range filter
    if fromdate:
        df = df[df.index >= pd.Timestamp(fromdate)]
    if todate:
        # Include all bars through the end of todate
        df = df[df.index < pd.Timestamp(todate) + pd.Timedelta(days=1)]

    # Regular Trading Hours filter: keep only 09:30–15:55 ET bars
    # The last 5-min bar starting at 15:55 covers 15:55–16:00, after which
    # the EOD close timer fires and flattens any open position.
    if rth_only:
        df = df.between_time('09:30', '15:55')

    if df.empty:
        raise ValueError(
            'No data found after filtering.\n'
            'Check --fromdate/--todate and verify the CSV covers that range.\n'
            'If using --fromdate/--todate, note that dates are inclusive.')

    print('Loaded {:,} bars  |  {} → {}  |  session: {}'.format(
        len(df),
        df.index[0].strftime('%Y-%m-%d'),
        df.index[-1].strftime('%Y-%m-%d'),
        'RTH only (09:30-16:00 ET)' if rth_only else 'all hours',
    ))

    return bt.feeds.PandasData(
        dataname=df,
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
        openinterest=-1,   # CSV has no open-interest column
    )


# ── Strategy ─────────────────────────────────────────────────────────────────

def dollars_to_points(dollars, contracts):
    """Convert a dollar P&L amount to NQ index points (for stop/target calc)."""
    return dollars / (contracts * MNQ_POINT_VALUE)


class TopstepMNQStrategy(EODPositionCloserMixin, bt.Strategy):
    """
    EMA50/EMA200 crossover strategy for Topstep MNQ combine rules.

    Golden cross  → long  3 MNQ with bracket orders ($150 stop / $150 target)
    Death  cross  → short 3 MNQ with bracket orders ($150 stop / $150 target)

    EODPositionCloserMixin flattens everything at 4:00 PM ET each day.
    """

    params = (
        ('ema_fast',       50),
        ('ema_slow',       200),
        ('contracts',      3),
        ('risk_dollars',   150.0),
        ('profit_dollars', 150.0),
        # EODPositionCloserMixin params
        ('close_time',         datetime.time(16, 0)),
        ('cancel_open_orders', True),
        ('printlog', False),
    )

    def __init__(self):
        super(TopstepMNQStrategy, self).__init__()
        self.ema_fast  = bt.indicators.EMA(self.data.close, period=self.p.ema_fast)
        self.ema_slow  = bt.indicators.EMA(self.data.close, period=self.p.ema_slow)
        self.crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)
        self.main_order = None   # tracks the main leg of the active bracket

    def log(self, txt):
        if self.p.printlog:
            print('{} | {}'.format(
                self.datetime.datetime(0).strftime('%Y-%m-%d %H:%M'), txt))

    def next(self):
        # Skip while a bracket is open or we already have a position
        if self.position or self.main_order is not None:
            super(TopstepMNQStrategy, self).next()
            return

        stop_pts   = dollars_to_points(self.p.risk_dollars,   self.p.contracts)
        target_pts = dollars_to_points(self.p.profit_dollars, self.p.contracts)
        entry = self.data.close[0]

        if self.crossover > 0:       # EMA50 crosses above EMA200 → long
            stop   = round(entry - stop_pts,   2)
            target = round(entry + target_pts, 2)
            self.log('LONG   entry≈{:.2f}  stop={:.2f}  target={:.2f}'.format(
                entry, stop, target))
            bracket = self.buy_bracket(
                size=self.p.contracts, stopprice=stop, limitprice=target)
            self.main_order = bracket[0]

        elif self.crossover < 0:     # EMA50 crosses below EMA200 → short
            stop   = round(entry + stop_pts,   2)
            target = round(entry - target_pts, 2)
            self.log('SHORT  entry≈{:.2f}  stop={:.2f}  target={:.2f}'.format(
                entry, stop, target))
            bracket = self.sell_bracket(
                size=self.p.contracts, stopprice=stop, limitprice=target)
            self.main_order = bracket[0]

        super(TopstepMNQStrategy, self).next()

    def notify_order(self, order):
        if order.status in (order.Completed, order.Canceled,
                            order.Rejected, order.Expired):
            if order is self.main_order:
                self.main_order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log('CLOSED  gross={:.2f}  net={:.2f}'.format(
                trade.pnl, trade.pnlcomm))


# ── Runner ───────────────────────────────────────────────────────────────────

def run(args=None):
    parser = argparse.ArgumentParser(
        description='Topstep MNQ EMA Crossover Backtest',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--data', required=True,
        help='Path to MNQ 5-min CSV (ts_event,Open,High,Low,Close,Volume)')
    parser.add_argument(
        '--fromdate', default=None, metavar='YYYY-MM-DD',
        help='Backtest start date (inclusive)')
    parser.add_argument(
        '--todate', default=None, metavar='YYYY-MM-DD',
        help='Backtest end date (inclusive)')
    parser.add_argument(
        '--rth-only', action='store_true',
        help='Restrict to Regular Trading Hours only (09:30-16:00 ET); default: all sessions')
    parser.add_argument(
        '--ema-fast', type=int, default=50, metavar='N',
        help='Fast EMA period')
    parser.add_argument(
        '--ema-slow', type=int, default=200, metavar='N',
        help='Slow EMA period')
    parser.add_argument(
        '--contracts', type=int, default=3, metavar='N',
        help='Contracts per trade')
    parser.add_argument(
        '--risk', type=float, default=150.0, metavar='$',
        help='Dollar risk per trade (stop loss total)')
    parser.add_argument(
        '--profit', type=float, default=150.0, metavar='$',
        help='Dollar profit target per trade')
    parser.add_argument(
        '--printlog', action='store_true',
        help='Print each signal and closed trade to stdout')
    args = parser.parse_args(args)

    rth_only = args.rth_only
    fromdate = (datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')
                if args.fromdate else None)
    todate   = (datetime.datetime.strptime(args.todate, '%Y-%m-%d')
                if args.todate else None)

    # ── Cerebro ──────────────────────────────────────────────────────────────
    cerebro = bt.Cerebro()

    # ── Data ─────────────────────────────────────────────────────────────────
    data = load_mnq_csv(args.data, fromdate=fromdate,
                        todate=todate, rth_only=rth_only)
    cerebro.adddata(data)

    # ── Broker ───────────────────────────────────────────────────────────────
    STARTING_BALANCE = 50000.0
    cerebro.broker.setcash(STARTING_BALANCE)
    cerebro.broker.addcommissioninfo(MNQFuturesCommInfo(commission=0.74))
    cerebro.broker.set_slippage_fixed(0.0)   # no slippage

    # ── Sizer: max 50 MNQ contracts (Topstep rule) ───────────────────────────
    cerebro.addsizer(MaxContractsSizer, max_contracts=50, stake=args.contracts)

    # ── Strategy ─────────────────────────────────────────────────────────────
    cerebro.addstrategy(
        TopstepMNQStrategy,
        ema_fast=args.ema_fast,
        ema_slow=args.ema_slow,
        contracts=args.contracts,
        risk_dollars=args.risk,
        profit_dollars=args.profit,
        printlog=args.printlog,
    )

    # ── Analyzers ────────────────────────────────────────────────────────────
    # Trailing drawdown: $2,000 limit; freeze trailing at $3,000 profit
    cerebro.addanalyzer(
        PropFirmDrawDown,
        _name='propfirm',
        max_drawdown=2000.0,
        trail_stop_threshold=3000.0,
        starting_balance=STARTING_BALANCE,
        trailing_mode='eod',
    )
    # Consistency: no single day > 50% of total net profit
    cerebro.addanalyzer(
        ConsistencyAnalyzer,
        _name='consistency',
        max_day_pct=50.0,
    )

    # ── Header ───────────────────────────────────────────────────────────────
    stop_pts = dollars_to_points(args.risk, args.contracts)
    print('=' * 62)
    print('  Topstep MNQ Combine — EMA{}/{} Crossover'.format(
        args.ema_fast, args.ema_slow))
    print('=' * 62)
    print('  Account balance : ${:>10,.0f}'.format(STARTING_BALANCE))
    print('  Instrument      : MNQ (Micro E-mini Nasdaq 100)')
    print('  Contracts/trade : {}'.format(args.contracts))
    print('  Risk per trade  : ${:.0f}  ({:.0f} NQ pts)'.format(
        args.risk, stop_pts))
    print('  Target per trade: ${:.0f}  ({:.0f} NQ pts)'.format(
        args.profit, stop_pts))
    print('  Session         : {}'.format(
        'RTH only  09:30–16:00 ET' if rth_only else 'All sessions (Asia + London + New York)'))
    print('  EOD close at    : 4:00 PM ET')
    print('  Fees            : $0.74/contract/side  (no slippage)')
    print('-' * 62)

    # ── Run ──────────────────────────────────────────────────────────────────
    results = cerebro.run()
    strat = results[0]

    ending_value = cerebro.broker.getvalue()
    net_pnl = ending_value - STARTING_BALANCE

    dd   = strat.analyzers.propfirm.get_analysis()
    cons = strat.analyzers.consistency.get_analysis()

    # ── Results ──────────────────────────────────────────────────────────────
    print('\n' + '=' * 62)
    print('  RESULTS')
    print('=' * 62)
    print('  Net P&L        : ${:>10,.2f}'.format(net_pnl))
    print('  Ending balance : ${:>10,.2f}'.format(ending_value))

    target_hit = net_pnl >= 3000.0
    remaining  = max(3000.0 - net_pnl, 0.0)
    print('  Profit target  : {}  (${:,.0f} / $3,000{})'.format(
        'PASSED' if target_hit else 'not reached',
        max(net_pnl, 0),
        '' if target_hit else '  —  ${:,.0f} to go'.format(remaining)))

    print('\n' + '-' * 62)
    print('  PROP FIRM RULE CHECK')
    print('-' * 62)

    # Trailing drawdown check
    dd_ok = not dd.breached
    print('  Trailing DD    : {}  (worst: ${:,.2f} / $2,000 limit)'.format(
        'PASS' if dd_ok else 'BREACHED', dd.max_drawdown))
    if dd.trailing_frozen:
        print('                   Trailing locked — profit target reached')
    if dd.breached:
        print('                   Breach events : {}'.format(dd.breach_count))
        for b in dd.breaches:
            print('                     {} | val=${:,.2f} | DD=${:,.2f}'.format(
                b['datetime'].strftime('%Y-%m-%d %H:%M'),
                b['value'], b['drawdown']))

    # Consistency check
    cons_ok = cons.consistent
    print('  Consistency    : {}'.format('PASS' if cons_ok else 'VIOLATED'))
    if not cons_ok:
        for v in cons.violations:
            print('    {} | ${:,.2f} ({:.1f}% of net profit)'.format(
                v['date'], v['pnl'], v['pct']))

    # Overall verdict
    print('-' * 62)
    all_pass = target_hit and dd_ok and cons_ok
    if all_pass:
        print('  COMBINE STATUS : PASSED — all rules met!')
    else:
        failed = []
        if not target_hit: failed.append('profit target not reached')
        if not dd_ok:      failed.append('drawdown limit breached')
        if not cons_ok:    failed.append('consistency rule violated')
        print('  COMBINE STATUS : FAILED ({})'.format(', '.join(failed)))

    # ── Daily P&L breakdown ──────────────────────────────────────────────────
    if cons.daily_pnl:
        print('\n' + '-' * 62)
        print('  DAILY P&L BREAKDOWN')
        print('-' * 62)
        for date in sorted(cons.daily_pnl):
            pnl = cons.daily_pnl[date]
            note = ''
            if cons.net_pnl > 0:
                pct = 100.0 * pnl / cons.net_pnl
                note = '  ({:.1f}%)'.format(pct)
                if pct > 50.0:
                    note += '  ← CONSISTENCY VIOLATION'
            print('  {}  ${:>9,.2f}{}'.format(date, pnl, note))

        if cons.best_day:
            print('\n  Best day : {} — ${:,.2f}'.format(
                cons.best_day['date'], cons.best_day['pnl']))
        print('  Trading days : {}'.format(len(cons.daily_pnl)))


if __name__ == '__main__':
    run()
