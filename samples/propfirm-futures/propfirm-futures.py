#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
'''
Prop Firm Futures Trading Sample
=================================

Demonstrates all prop firm components working together:

  1. FuturesCommInfo — tick-aware commission/P&L for ES futures
  2. PropFirmDrawDown — trailing drawdown analyzer with breach detection
  3. EODPositionCloserMixin — auto-close all positions at a set time
  4. MaxContractsSizer — cap maximum open contracts

The strategy is a simple SMA crossover on 5-minute ES futures data.
Prop firm rules enforce:
  - $2,500 max trailing drawdown (EOD trailing)
  - Trail stops after $3,000 profit (HWM freezes at threshold)
  - Max 3 contracts at a time
  - All positions closed by 3:55 PM

Usage::

    python propfirm-futures.py
    python propfirm-futures.py --max-dd 3000 --max-contracts 5
    python propfirm-futures.py --trailing-mode intraday
    python propfirm-futures.py --close-time 15:30
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import datetime
import os
import sys

import backtrader as bt

from backtrader.commissions.futures import ESFuturesCommInfo
from backtrader.analyzers.propfirm_drawdown import PropFirmDrawDown
from backtrader.sizers.max_contracts import MaxContractsSizer
from backtrader.strategies.position_closer import EODPositionCloserMixin


class PropFirmStrategy(EODPositionCloserMixin, bt.Strategy):
    '''SMA crossover strategy with prop firm EOD position closing.

    The EODPositionCloserMixin automatically flattens all positions at
    close_time. The strategy only needs to define close_time and
    cancel_open_orders as params — the mixin reads them via getattr.
    '''

    params = (
        # Mixin params
        ('close_time', datetime.time(15, 55)),
        ('cancel_open_orders', True),
        # Strategy params
        ('fast_period', 10),
        ('slow_period', 30),
        ('printlog', False),
    )

    def __init__(self):
        super(PropFirmStrategy, self).__init__()

        self.sma_fast = bt.indicators.SMA(self.data.close,
                                          period=self.p.fast_period)
        self.sma_slow = bt.indicators.SMA(self.data.close,
                                          period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

        self.order = None

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datetime.datetime(0)
            print('{} {}'.format(dt.isoformat(), txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed:
            if order.isbuy():
                self.log('BUY @ {:.2f}, size={}'.format(
                    order.executed.price, order.executed.size))
            else:
                self.log('SELL @ {:.2f}, size={}'.format(
                    order.executed.price, order.executed.size))

        self.order = None

    def next(self):
        # Don't trade if we have a pending order
        if self.order:
            return

        # Don't open new positions too close to close_time
        bar_time = self.datetime.time()
        if bar_time >= datetime.time(15, 45):
            return

        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
                self.log('BUY SIGNAL @ {:.2f}'.format(self.data.close[0]))
            elif self.crossover < 0:
                self.order = self.sell()
                self.log('SELL SIGNAL @ {:.2f}'.format(self.data.close[0]))
        else:
            if self.position.size > 0 and self.crossover < 0:
                self.order = self.close()
                self.log('CLOSE LONG @ {:.2f}'.format(self.data.close[0]))
            elif self.position.size < 0 and self.crossover > 0:
                self.order = self.close()
                self.log('CLOSE SHORT @ {:.2f}'.format(self.data.close[0]))


def run(args=None):
    parser = argparse.ArgumentParser(
        description='Prop Firm Futures Trading Sample',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--data', default=None,
                        help='Path to data file (default: bundled 5-min data)')
    parser.add_argument('--cash', type=float, default=50000.0,
                        help='Starting cash (default: 50000)')
    parser.add_argument('--max-dd', type=float, default=2500.0,
                        help='Max trailing drawdown in dollars (default: 2500)')
    parser.add_argument('--trailing-mode', default='eod',
                        choices=['eod', 'intraday'],
                        help='Trailing drawdown mode (default: eod)')
    parser.add_argument('--trail-stop', type=float, default=3000.0,
                        help='Profit at which trailing stops (default: 3000)')
    parser.add_argument('--max-contracts', type=int, default=3,
                        help='Max contracts at once (default: 3)')
    parser.add_argument('--close-time', default='15:55',
                        help='Time to close all positions HH:MM (default: 15:55)')
    parser.add_argument('--fast', type=int, default=10,
                        help='Fast SMA period (default: 10)')
    parser.add_argument('--slow', type=int, default=30,
                        help='Slow SMA period (default: 30)')
    parser.add_argument('--printlog', action='store_true',
                        help='Print trade log')
    parser.add_argument('--plot', action='store_true',
                        help='Plot results')

    args = parser.parse_args(args)

    # Parse close_time
    h, m = args.close_time.split(':')
    close_time = datetime.time(int(h), int(m))

    cerebro = bt.Cerebro()

    # --- Data ---
    if args.data:
        datapath = args.data
    else:
        modpath = os.path.dirname(os.path.abspath(__file__))
        datapath = os.path.join(modpath, '..', '..', 'datas',
                                '2006-min-005.txt')

    data = bt.feeds.BacktraderCSVData(
        dataname=datapath,
        fromdate=datetime.datetime(2006, 1, 2),
        todate=datetime.datetime(2006, 1, 31),
    )
    cerebro.adddata(data)

    # --- Component 1: Futures Commission Info ---
    cerebro.broker.addcommissioninfo(ESFuturesCommInfo(), name=None)
    cerebro.broker.setcash(args.cash)

    # --- Component 2: Prop Firm Drawdown Analyzer ---
    cerebro.addanalyzer(
        PropFirmDrawDown,
        max_drawdown=args.max_dd,
        trailing_mode=args.trailing_mode,
        trail_stop_threshold=args.trail_stop,
        starting_balance=args.cash,
    )

    # Also add the built-in DrawDown for comparison
    cerebro.addanalyzer(bt.analyzers.DrawDown)

    # --- Component 3: EOD Position Closer (via strategy mixin) ---
    cerebro.addstrategy(
        PropFirmStrategy,
        close_time=close_time,
        fast_period=args.fast,
        slow_period=args.slow,
        printlog=args.printlog,
    )

    # --- Component 4: Max Contracts Sizer ---
    cerebro.addsizer(MaxContractsSizer,
                     max_contracts=args.max_contracts, stake=1)

    # --- Run ---
    print('=' * 60)
    print('Prop Firm Futures Backtest')
    print('=' * 60)
    print('Starting cash:      ${:,.2f}'.format(args.cash))
    print('Instrument:         ES (E-mini S&P 500)')
    print('Commission:         $2.25/contract/side')
    print('Tick size:          0.25 ($12.50/tick)')
    print('Max drawdown:       ${:,.2f}'.format(args.max_dd))
    print('Trailing mode:      {}'.format(args.trailing_mode))
    print('Trail stops after:  ${:,.2f} profit'.format(args.trail_stop))
    print('Max contracts:      {}'.format(args.max_contracts))
    print('Close time:         {}'.format(close_time))
    print('SMA periods:        {}/{}'.format(args.fast, args.slow))
    print('=' * 60)

    results = cerebro.run()
    strat = results[0]

    # --- Results ---
    print()
    print('Final portfolio:    ${:,.2f}'.format(cerebro.broker.getvalue()))

    # Prop firm drawdown results
    dd = strat.analyzers.propfirmdrawdown.get_analysis()
    print()
    print('--- Prop Firm Drawdown ---')
    print('High-water mark:    ${:,.2f}'.format(dd.hwm))
    print('Max drawdown:       ${:,.2f}'.format(dd.max_drawdown))
    print('Current drawdown:   ${:,.2f}'.format(dd.current_drawdown))
    print('Trailing frozen:    {}'.format(dd.trailing_frozen))
    if dd.frozen_hwm is not None:
        print('Frozen HWM:         ${:,.2f}'.format(dd.frozen_hwm))
    print('Breached:           {}'.format(dd.breached))
    if dd.breached:
        print('Breach count:       {}'.format(dd.breach_count))
        for i, b in enumerate(dd.breaches):
            print('  Breach {}: {} DD=${:,.2f} (value=${:,.2f})'.format(
                i + 1, b['datetime'], b['drawdown'], b['value']))

    # Built-in drawdown for comparison
    builtin_dd = strat.analyzers.drawdown.get_analysis()
    print()
    print('--- Built-in DrawDown (for comparison) ---')
    print('Max drawdown:       {:.2f}%'.format(builtin_dd.max.drawdown))
    print('Max money down:     ${:,.2f}'.format(builtin_dd.max.moneydown))

    print()
    if dd.breached:
        print('RESULT: PROP FIRM RULES VIOLATED')
    else:
        print('RESULT: PROP FIRM RULES PASSED')

    if args.plot:
        cerebro.plot()


if __name__ == '__main__':
    run()
