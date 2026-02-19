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
  $150 risk  = $50/contract = 25 NQ points
  $150 target = $50/contract = 25 NQ points

Usage:
  python topstep-mnq.py --data /path/to/mnq_5min.csv
  python topstep-mnq.py --data /path/to/mnq_5min.csv --printlog
  python topstep-mnq.py --data /path/to/mnq_5min.csv --fromdate 2024-01-01 --todate 2024-06-30

Data format (GenericCSVData):
  The CSV file should have columns:
    datetime, open, high, low, close, volume
  with datetime in the format %Y-%m-%d %H:%M:%S (5-minute bars).
  Adjust --dtformat and --timeframe/--compression below if your format differs.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import backtrader as bt
from backtrader.commissions.futures import MNQFuturesCommInfo
from backtrader.analyzers.propfirm_drawdown import PropFirmDrawDown
from backtrader.analyzers.consistency import ConsistencyAnalyzer
from backtrader.strategies.position_closer import EODPositionCloserMixin
from backtrader.sizers.max_contracts import MaxContractsSizer


# MNQ point value: tick_value / tick_size = $0.50 / 0.25 = $2.00 per NQ point per contract
_MNQ_COMM = MNQFuturesCommInfo()
MNQ_POINT_VALUE = _MNQ_COMM.p.tick_value / _MNQ_COMM.p.tick_size


def dollars_to_points(dollars, contracts):
    """Convert a dollar P&L target to NQ index points."""
    return dollars / (contracts * MNQ_POINT_VALUE)


class TopstepMNQStrategy(EODPositionCloserMixin, bt.Strategy):
    """
    EMA50/EMA200 crossover strategy sized for Topstep MNQ combine rules.

    On a golden cross (EMA50 > EMA200):  open long 3 MNQ with bracket orders.
    On a death cross (EMA50 < EMA200):   open short 3 MNQ with bracket orders.

    EODPositionCloserMixin closes all positions at 4:00 PM ET.
    """

    params = (
        # Indicator periods
        ('ema_fast', 50),
        ('ema_slow', 200),

        # Trade sizing and risk
        ('contracts', 3),         # contracts per trade
        ('risk_dollars', 150.0),  # max dollar loss per trade
        ('profit_dollars', 150.0),# dollar profit target per trade

        # EODPositionCloserMixin — close everything by 4:00 PM ET
        ('close_time', datetime.time(16, 0)),
        ('cancel_open_orders', True),

        # Output
        ('printlog', False),
    )

    def __init__(self):
        super(TopstepMNQStrategy, self).__init__()
        self.ema_fast = bt.indicators.EMA(
            self.data.close, period=self.p.ema_fast)
        self.ema_slow = bt.indicators.EMA(
            self.data.close, period=self.p.ema_slow)
        self.crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)

        # Track the main bracket order so we don't double-enter
        self.main_order = None

    def log(self, txt):
        if self.p.printlog:
            dt = self.datetime.datetime(0)
            print('{} | {}'.format(dt.strftime('%Y-%m-%d %H:%M'), txt))

    def next(self):
        # Already in a position or waiting for a bracket order to fill — skip
        if self.position or self.main_order is not None:
            super(TopstepMNQStrategy, self).next()
            return

        # Calculate stop/target distances in NQ index points
        stop_pts = dollars_to_points(self.p.risk_dollars, self.p.contracts)
        target_pts = dollars_to_points(self.p.profit_dollars, self.p.contracts)
        entry = self.data.close[0]

        if self.crossover > 0:   # EMA50 crosses above EMA200 → long
            stop = round(entry - stop_pts, 2)
            target = round(entry + target_pts, 2)
            self.log('LONG  entry≈{:.2f}  stop={:.2f}  target={:.2f}'.format(
                entry, stop, target))
            bracket = self.buy_bracket(
                size=self.p.contracts,
                stopprice=stop,
                limitprice=target,
            )
            self.main_order = bracket[0]

        elif self.crossover < 0:  # EMA50 crosses below EMA200 → short
            stop = round(entry + stop_pts, 2)
            target = round(entry - target_pts, 2)
            self.log('SHORT entry≈{:.2f}  stop={:.2f}  target={:.2f}'.format(
                entry, stop, target))
            bracket = self.sell_bracket(
                size=self.p.contracts,
                stopprice=stop,
                limitprice=target,
            )
            self.main_order = bracket[0]

        super(TopstepMNQStrategy, self).next()

    def notify_order(self, order):
        if order.status in (order.Completed, order.Canceled,
                            order.Rejected, order.Expired):
            if order is self.main_order:
                self.main_order = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.log('CLOSED  pnl={:.2f}  net={:.2f}'.format(
                trade.pnl, trade.pnlcomm))


def run(args=None):
    parser = argparse.ArgumentParser(
        description='Topstep MNQ EMA Crossover Backtest')
    parser.add_argument(
        '--data', required=True,
        help='Path to MNQ 5-minute OHLCV CSV file')
    parser.add_argument(
        '--fromdate', default=None,
        help='Start date YYYY-MM-DD (default: all data)')
    parser.add_argument(
        '--todate', default=None,
        help='End date YYYY-MM-DD (default: all data)')
    parser.add_argument(
        '--dtformat', default='%Y-%m-%d %H:%M:%S',
        help='Datetime format string in your CSV (default: %%Y-%%m-%%d %%H:%%M:%%S)')
    parser.add_argument(
        '--ema-fast', type=int, default=50,
        help='Fast EMA period (default: 50)')
    parser.add_argument(
        '--ema-slow', type=int, default=200,
        help='Slow EMA period (default: 200)')
    parser.add_argument(
        '--contracts', type=int, default=3,
        help='Contracts per trade (default: 3)')
    parser.add_argument(
        '--risk', type=float, default=150.0,
        help='Dollar risk per trade (default: 150)')
    parser.add_argument(
        '--profit', type=float, default=150.0,
        help='Dollar profit target per trade (default: 150)')
    parser.add_argument(
        '--printlog', action='store_true',
        help='Print each trade signal to stdout')
    args = parser.parse_args(args)

    fromdate = (datetime.datetime.strptime(args.fromdate, '%Y-%m-%d')
                if args.fromdate else None)
    todate = (datetime.datetime.strptime(args.todate, '%Y-%m-%d')
              if args.todate else None)

    # ── Cerebro ─────────────────────────────────────────────────────────────
    cerebro = bt.Cerebro()

    # ── Data ────────────────────────────────────────────────────────────────
    data_kwargs = dict(
        dataname=args.data,
        dtformat=args.dtformat,
        timeframe=bt.TimeFrame.Minutes,
        compression=5,
        openinterest=-1,   # no OI column; set to -1 to ignore
    )
    if fromdate:
        data_kwargs['fromdate'] = fromdate
    if todate:
        data_kwargs['todate'] = todate

    data = bt.feeds.GenericCSVData(**data_kwargs)
    cerebro.adddata(data)

    # ── Broker ──────────────────────────────────────────────────────────────
    STARTING_BALANCE = 50000.0
    cerebro.broker.setcash(STARTING_BALANCE)
    cerebro.broker.addcommissioninfo(MNQFuturesCommInfo())

    # ── Sizer ───────────────────────────────────────────────────────────────
    # Safety cap at 50 MNQ contracts (Topstep rule).
    # The strategy passes size= explicitly to buy_bracket/sell_bracket,
    # so this sizer only applies to any bare buy()/sell() calls.
    cerebro.addsizer(MaxContractsSizer, max_contracts=50, stake=args.contracts)

    # ── Strategy ────────────────────────────────────────────────────────────
    cerebro.addstrategy(
        TopstepMNQStrategy,
        ema_fast=args.ema_fast,
        ema_slow=args.ema_slow,
        contracts=args.contracts,
        risk_dollars=args.risk,
        profit_dollars=args.profit,
        printlog=args.printlog,
    )

    # ── Analyzers ───────────────────────────────────────────────────────────

    # Trailing drawdown: $2,000 limit; freeze at $3,000 profit (Topstep rule)
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

    # ── Run ─────────────────────────────────────────────────────────────────
    print('=' * 60)
    print('Topstep MNQ Combine — EMA{}/{} Crossover'.format(
        args.ema_fast, args.ema_slow))
    print('=' * 60)
    print('Account:           ${:,.0f}'.format(STARTING_BALANCE))
    print('Instrument:        MNQ (Micro E-mini Nasdaq)')
    print('Contracts/trade:   {}'.format(args.contracts))
    print('Risk/trade:        ${:.0f}'.format(args.risk))
    print('Target/trade:      ${:.0f}'.format(args.profit))
    print('Stop/target pts:   {:.1f} NQ points'.format(
        dollars_to_points(args.risk, args.contracts)))
    print('EOD close by:      4:00 PM ET')
    print('-' * 60)

    results = cerebro.run()
    strat = results[0]

    ending_value = cerebro.broker.getvalue()
    net_pnl = ending_value - STARTING_BALANCE

    dd = strat.analyzers.propfirm.get_analysis()
    cons = strat.analyzers.consistency.get_analysis()

    # ── Summary ─────────────────────────────────────────────────────────────
    print('\n' + '=' * 60)
    print('RESULTS')
    print('=' * 60)
    print('Net P&L:           ${:,.2f}'.format(net_pnl))
    print('Ending Balance:    ${:,.2f}'.format(ending_value))

    target_hit = net_pnl >= 3000.0
    print('Profit Target:     {} (${:,.0f} / $3,000)'.format(
        'PASSED ✓' if target_hit else 'not reached', max(net_pnl, 0)))

    print('\n' + '-' * 60)
    print('PROP FIRM RULE CHECK')
    print('-' * 60)

    # Trailing drawdown
    dd_ok = not dd.breached
    print('Trailing Drawdown: {} (max hit: ${:,.2f} / $2,000 limit)'.format(
        'PASS ✓' if dd_ok else 'BREACHED ✗', dd.max_drawdown))
    if dd.trailing_frozen:
        print('                   Trailing stopped (profit target locked in)')
    if dd.breached:
        print('                   Breach events: {}'.format(dd.breach_count))

    # Consistency
    cons_ok = cons.consistent
    print('Consistency Rule:  {}'.format(
        'PASS ✓' if cons_ok else 'VIOLATED ✗'))
    if not cons_ok:
        for v in cons.violations:
            print('  Violation {}: ${:,.2f} ({:.1f}% of net profit)'.format(
                v['date'], v['pnl'], v['pct']))

    # Overall
    print('-' * 60)
    all_pass = target_hit and dd_ok and cons_ok
    print('COMBINE STATUS:    {}'.format(
        'PASSED — all rules met!' if all_pass else 'FAILED — see violations above'))

    # ── Daily P&L breakdown ─────────────────────────────────────────────────
    if cons.daily_pnl:
        print('\n' + '-' * 60)
        print('DAILY P&L BREAKDOWN')
        print('-' * 60)
        for date in sorted(cons.daily_pnl):
            pnl = cons.daily_pnl[date]
            flag = ''
            if cons.net_pnl > 0:
                pct = 100.0 * pnl / cons.net_pnl
                flag = '  ← {:.1f}%'.format(pct)
                if pct > 50.0:
                    flag += ' VIOLATION'
            print('  {}: ${:,.2f}{}'.format(date, pnl, flag))
        if cons.best_day:
            print('\nBest day: {} — ${:,.2f}'.format(
                cons.best_day['date'], cons.best_day['pnl']))


if __name__ == '__main__':
    run()
