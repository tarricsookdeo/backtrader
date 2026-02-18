#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import testcommon

import backtrader as bt
from backtrader.sizers.max_contracts import MaxContractsSizer


class BuyEveryBarStrategy(bt.Strategy):
    '''Buys every bar to test that the sizer caps position size.'''
    params = (('max_expected', 3),)

    def __init__(self):
        self.max_seen = 0

    def next(self):
        self.buy()
        pos = self.broker.getposition(self.data)
        if pos.size > self.max_seen:
            self.max_seen = pos.size

    def stop(self):
        assert self.max_seen <= self.p.max_expected, \
            'Position {} exceeded max {}'.format(
                self.max_seen, self.p.max_expected)


class SellEveryBarStrategy(bt.Strategy):
    '''Sells every bar to test short-side capping.'''
    params = (('max_expected', 3),)

    def __init__(self):
        self.min_seen = 0

    def next(self):
        self.sell()
        pos = self.broker.getposition(self.data)
        if pos.size < self.min_seen:
            self.min_seen = pos.size

    def stop(self):
        assert abs(self.min_seen) <= self.p.max_expected, \
            'Position {} exceeded max {}'.format(
                self.min_seen, self.p.max_expected)


class FlipStrategy(bt.Strategy):
    '''Alternates buy/sell signals to test capping during reversals.'''
    params = (('max_expected', 2),)

    def __init__(self):
        self.max_seen = 0
        self.count = 0

    def next(self):
        self.count += 1
        if self.count % 10 < 5:
            self.buy()
        else:
            self.sell()
        pos = self.broker.getposition(self.data)
        if abs(pos.size) > self.max_seen:
            self.max_seen = abs(pos.size)

    def stop(self):
        assert self.max_seen <= self.p.max_expected, \
            'Position {} exceeded max {}'.format(
                self.max_seen, self.p.max_expected)


def check_long_cap():
    '''Position should never exceed max_contracts when buying.'''
    max_c = 3
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.addstrategy(BuyEveryBarStrategy, max_expected=max_c)
    cerebro.addsizer(MaxContractsSizer, max_contracts=max_c, stake=1)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_short_cap():
    '''Position should never exceed -max_contracts when selling.'''
    max_c = 3
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.addstrategy(SellEveryBarStrategy, max_expected=max_c)
    cerebro.addsizer(MaxContractsSizer, max_contracts=max_c, stake=1)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_flip_cap():
    '''Position should stay within bounds during buy/sell alternation.'''
    max_c = 2
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.addstrategy(FlipStrategy, max_expected=max_c)
    cerebro.addsizer(MaxContractsSizer, max_contracts=max_c, stake=1)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_stake_larger_than_max():
    '''When stake > max_contracts, size should be capped to max_contracts.'''
    max_c = 2
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.addstrategy(BuyEveryBarStrategy, max_expected=max_c)
    cerebro.addsizer(MaxContractsSizer, max_contracts=max_c, stake=5)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_returns_zero_at_limit():
    '''Sizer should return 0 when already at max position.'''
    sizer = MaxContractsSizer(max_contracts=3, stake=1)

    class FakePosition:
        size = 3

    class FakeStrategy:
        def getposition(self, data):
            return FakePosition()

    sizer.strategy = FakeStrategy()
    sizer.broker = None

    result = sizer._getsizing(None, 100000, None, isbuy=True)
    assert result == 0, 'Expected 0, got {}'.format(result)

    # Selling should still work (moving toward flat)
    result_sell = sizer._getsizing(None, 100000, None, isbuy=False)
    assert result_sell == 1, 'Expected 1, got {}'.format(result_sell)


def test_run(main=False):
    check_long_cap()
    check_short_cap()
    check_flip_cap()
    check_stake_larger_than_max()
    check_returns_zero_at_limit()

    if main:
        print('All MaxContractsSizer tests passed')


if __name__ == '__main__':
    test_run(main=True)
