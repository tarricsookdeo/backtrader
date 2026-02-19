#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import datetime

import testcommon

import backtrader as bt
from backtrader.commissions.futures import ESFuturesCommInfo, FuturesCommInfo
from backtrader.sizers.risk_per_trade import RiskPerTradeSizer


modpath = os.path.dirname(os.path.abspath(__file__))


def _make_cerebro(risk_per_trade=None, stop_ticks=None, tick_value=None,
                  comminfo=None):
    '''Build a cerebro with RiskPerTradeSizer and run it. Returns strategy.'''
    cerebro = bt.Cerebro()
    datapath = os.path.join(modpath, '..', 'datas', '2006-day-001.txt')
    data = bt.feeds.BacktraderCSVData(
        dataname=datapath,
        fromdate=datetime.datetime(2006, 1, 1),
        todate=datetime.datetime(2006, 3, 1),
    )
    cerebro.adddata(data)

    if comminfo is None:
        comminfo = ESFuturesCommInfo()
    cerebro.broker.addcommissioninfo(comminfo)
    cerebro.broker.setcash(500000)

    kwargs = {}
    if risk_per_trade is not None:
        kwargs['risk_per_trade'] = risk_per_trade
    if stop_ticks is not None:
        kwargs['stop_ticks'] = stop_ticks
    if tick_value is not None:
        kwargs['tick_value'] = tick_value

    cerebro.addsizer(RiskPerTradeSizer, **kwargs)

    class SingleBuyStrategy(bt.Strategy):
        def __init__(self):
            self.order = None
            self.order_size = None

        def next(self):
            if self.order is None and not self.position:
                self.order = self.buy()

        def notify_order(self, order):
            if order.status == order.Completed:
                self.order_size = order.executed.size

    cerebro.addstrategy(SingleBuyStrategy)
    results = cerebro.run()
    return results[0]


def check_basic_sizing():
    '''risk=100, stop_ticks=4, tick_value=12.50 -> floor(100/50) = 2'''
    strat = _make_cerebro(risk_per_trade=100.0, stop_ticks=4)
    assert strat.order_size == 2, \
        'Expected size 2, got {}'.format(strat.order_size)


def check_auto_detect_tick_value():
    '''tick_value should be auto-detected from ESFuturesCommInfo'''
    # ES tick_value=12.50, stop_ticks=4 -> 100/(4*12.50) = 2
    strat = _make_cerebro(risk_per_trade=100.0, stop_ticks=4)
    assert strat.order_size == 2


def check_explicit_tick_value_override():
    '''Explicit tick_value param overrides comminfo'''
    # Force tick_value=25.0: 200/(4*25) = 2
    strat = _make_cerebro(risk_per_trade=200.0, stop_ticks=4, tick_value=25.0)
    assert strat.order_size == 2, \
        'Expected size 2, got {}'.format(strat.order_size)


def check_larger_risk_more_contracts():
    '''Doubling risk_per_trade doubles the size'''
    strat2 = _make_cerebro(risk_per_trade=100.0, stop_ticks=4)
    strat4 = _make_cerebro(risk_per_trade=200.0, stop_ticks=4)
    assert strat4.order_size == strat2.order_size * 2


def check_tighter_stop_fewer_contracts():
    '''Fewer stop_ticks means more cost per contract -> smaller size'''
    strat_wide = _make_cerebro(risk_per_trade=100.0, stop_ticks=4)
    strat_tight = _make_cerebro(risk_per_trade=100.0, stop_ticks=8)
    assert strat_tight.order_size < strat_wide.order_size


def check_zero_size_when_risk_too_small():
    '''Size is 0 (no order) when risk < cost of one tick'''
    # tick_value=12.50, stop_ticks=4 -> cost per contract = 50
    # risk=10 < 50 -> size = 0
    strat = _make_cerebro(risk_per_trade=10.0, stop_ticks=4)
    # order_size stays None because size=0 means no order is placed
    assert strat.order_size is None, \
        'Expected no order placed when size=0, got {}'.format(strat.order_size)


def check_invalid_stop_ticks_raises():
    '''stop_ticks=0 should raise ValueError'''
    try:
        _make_cerebro(risk_per_trade=100.0, stop_ticks=0)
        assert False, 'Should have raised ValueError'
    except ValueError:
        pass


def check_missing_tick_value_raises():
    '''Non-FuturesCommInfo without tick_value param should raise ValueError'''
    # Use a plain stock comminfo (no tick_value attribute on params)
    plain_comm = bt.CommInfoBase(stocklike=True)
    try:
        _make_cerebro(risk_per_trade=100.0, stop_ticks=4, comminfo=plain_comm)
        assert False, 'Should have raised ValueError'
    except ValueError:
        pass


def test_run(main=False):
    check_basic_sizing()
    check_auto_detect_tick_value()
    check_explicit_tick_value_override()
    check_larger_risk_more_contracts()
    check_tighter_stop_fewer_contracts()
    check_zero_size_when_risk_too_small()
    check_invalid_stop_ticks_raises()
    check_missing_tick_value_raises()

    if main:
        print('All RiskPerTradeSizer tests passed')


if __name__ == '__main__':
    test_run(main=True)
