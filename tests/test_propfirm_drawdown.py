#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import os

import testcommon

import backtrader as bt
from backtrader.analyzers.propfirm_drawdown import PropFirmDrawDown


modpath = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Strategy that buys once and holds (will have drawdown from price movement)
# ---------------------------------------------------------------------------
class BuyAndHoldStrategy(bt.Strategy):
    params = (('main', False),)

    def __init__(self):
        self.bought = False

    def next(self):
        if not self.bought:
            self.buy()
            self.bought = True


# ---------------------------------------------------------------------------
# Strategy that deliberately loses money (sells high, buys back low pattern)
# to force a known drawdown
# ---------------------------------------------------------------------------
class LosingStrategy(bt.Strategy):
    '''Buys and sells to generate losses, ensuring drawdown occurs.'''
    params = (('main', False),)

    def __init__(self):
        self.order_count = 0

    def next(self):
        # Buy on first bar, sell on 5th, buy on 10th, etc.
        # This creates realized losses from whipsawing
        self.order_count += 1
        if self.order_count == 1:
            self.buy()
        elif self.order_count == 5:
            self.close()
            self.sell()
        elif self.order_count == 10:
            self.close()


def _run_with_analyzer(strategy, cash=100000, max_dd=3000,
                       trailing_mode='intraday', trail_stop=None,
                       daily=True):
    '''Helper to run a strategy with the PropFirmDrawDown analyzer.'''
    cerebro = bt.Cerebro()

    if daily:
        data = testcommon.getdata(0)
    else:
        datapath = os.path.join(modpath, '..', 'datas', '2006-min-005.txt')
        data = bt.feeds.BacktraderCSVData(
            dataname=datapath,
            fromdate=datetime.datetime(2006, 1, 2),
            todate=datetime.datetime(2006, 1, 20),
        )

    cerebro.adddata(data)
    cerebro.addstrategy(strategy)
    cerebro.broker.setcash(cash)
    cerebro.addanalyzer(
        PropFirmDrawDown,
        max_drawdown=max_dd,
        trailing_mode=trailing_mode,
        trail_stop_threshold=trail_stop,
        starting_balance=cash,
    )

    results = cerebro.run()
    strat = results[0]
    return strat.analyzers[0].get_analysis()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def check_basic_tracking():
    '''HWM and drawdown should be tracked in intraday mode.'''
    analysis = _run_with_analyzer(BuyAndHoldStrategy, cash=100000,
                                  max_dd=50000)

    assert analysis.hwm > 0, 'HWM should be positive'
    assert analysis.hwm >= analysis.current_value, \
        'HWM should be >= current value'
    assert analysis.current_drawdown >= 0, \
        'Drawdown should be non-negative'
    assert analysis.max_drawdown >= analysis.current_drawdown, \
        'Max drawdown should be >= current drawdown'
    assert not analysis.breached, \
        'Should not be breached with 50k max_dd on 100k account'


def check_breach_detection():
    '''Drawdown exceeding max_drawdown should record a breach.'''
    # Use a tiny max_drawdown so any price movement triggers a breach
    analysis = _run_with_analyzer(BuyAndHoldStrategy, cash=100000,
                                  max_dd=1.0)

    assert analysis.breached, 'Should be breached with $1 max_dd'
    assert analysis.breach_count > 0, 'Should have breach events'
    assert len(analysis.breaches) > 0, 'Breaches list should not be empty'

    # Verify breach structure
    breach = analysis.breaches[0]
    assert 'datetime' in breach
    assert 'value' in breach
    assert 'drawdown' in breach
    assert 'hwm' in breach
    assert breach['drawdown'] > 1.0, \
        'Breach drawdown should exceed max_dd of $1'


def check_no_breach():
    '''Large max_drawdown should never be breached.'''
    analysis = _run_with_analyzer(BuyAndHoldStrategy, cash=100000,
                                  max_dd=999999)

    assert not analysis.breached
    assert analysis.breach_count == 0
    assert len(analysis.breaches) == 0


def check_hwm_updates_intraday():
    '''In intraday mode, HWM should update every bar as value grows.'''
    analysis = _run_with_analyzer(BuyAndHoldStrategy, cash=100000,
                                  max_dd=50000, trailing_mode='intraday')

    # HWM should be at least the starting balance
    assert analysis.hwm >= 100000, \
        'HWM should be >= starting balance, got {}'.format(analysis.hwm)


def check_eod_mode():
    '''EOD mode should still track drawdown (for daily data, same as intraday).'''
    analysis = _run_with_analyzer(BuyAndHoldStrategy, cash=100000,
                                  max_dd=50000, trailing_mode='eod')

    assert analysis.hwm > 0, 'HWM should be positive in EOD mode'
    assert analysis.max_drawdown >= 0, 'Max drawdown should be non-negative'


def check_eod_vs_intraday_with_intraday_data():
    '''With intraday data, EOD mode should update HWM less frequently
    than intraday mode, potentially resulting in different HWM values.'''
    analysis_intra = _run_with_analyzer(
        BuyAndHoldStrategy, cash=100000, max_dd=50000,
        trailing_mode='intraday', daily=False)

    analysis_eod = _run_with_analyzer(
        BuyAndHoldStrategy, cash=100000, max_dd=50000,
        trailing_mode='eod', daily=False)

    # Both should have valid HWM values
    assert analysis_intra.hwm > 0
    assert analysis_eod.hwm > 0

    # Intraday HWM should be >= EOD HWM (updates more frequently)
    assert analysis_intra.hwm >= analysis_eod.hwm, \
        'Intraday HWM {} should be >= EOD HWM {}'.format(
            analysis_intra.hwm, analysis_eod.hwm)


def check_trail_stop_freezes_hwm():
    '''Once trail_stop_threshold is reached, HWM should freeze at the
    threshold level (starting_balance + trail_stop_threshold).'''
    # Starting balance 100k, trail stops at +1 dollar profit
    # Any price gain will trigger the freeze
    analysis = _run_with_analyzer(
        BuyAndHoldStrategy, cash=100000, max_dd=50000,
        trail_stop=1.0)

    assert analysis.trailing_frozen, \
        'Trailing should be frozen (threshold is just $1 profit)'
    assert analysis.frozen_hwm == 100001.0, \
        'Frozen HWM should be at threshold level (100001), got {}'.format(
            analysis.frozen_hwm)


def check_trail_stop_not_reached():
    '''With a very high trail_stop_threshold, trailing should not freeze.'''
    analysis = _run_with_analyzer(
        BuyAndHoldStrategy, cash=100000, max_dd=50000,
        trail_stop=999999.0)

    assert not analysis.trailing_frozen, \
        'Trailing should not be frozen with unreachable threshold'
    assert analysis.frozen_hwm is None


def check_convenience_methods():
    '''is_breached() and get_current_drawdown() should work.'''
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.addstrategy(BuyAndHoldStrategy)
    cerebro.broker.setcash(100000)
    cerebro.addanalyzer(PropFirmDrawDown, max_drawdown=50000)

    results = cerebro.run()
    analyzer = results[0].analyzers[0]

    assert isinstance(analyzer.is_breached(), bool)
    assert isinstance(analyzer.get_current_drawdown(), float)


def check_starting_balance_auto_detect():
    '''If starting_balance is not set, it should be auto-detected.'''
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.addstrategy(BuyAndHoldStrategy)
    cerebro.broker.setcash(75000)
    cerebro.addanalyzer(PropFirmDrawDown, max_drawdown=50000)

    results = cerebro.run()
    analyzer = results[0].analyzers[0]
    analysis = analyzer.get_analysis()

    # HWM should start near the cash value
    assert analysis.hwm >= 75000, \
        'HWM should reflect starting cash, got {}'.format(analysis.hwm)


def test_run(main=False):
    check_basic_tracking()
    check_breach_detection()
    check_no_breach()
    check_hwm_updates_intraday()
    check_eod_mode()
    check_eod_vs_intraday_with_intraday_data()
    check_trail_stop_freezes_hwm()
    check_trail_stop_not_reached()
    check_convenience_methods()
    check_starting_balance_auto_detect()

    if main:
        print('All PropFirmDrawDown tests passed')


if __name__ == '__main__':
    test_run(main=True)
