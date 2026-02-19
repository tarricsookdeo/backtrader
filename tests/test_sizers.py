#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
'''Tests for PercentSizer, AllInSizer, and their integer variants.'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import testcommon

import backtrader as bt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class RecordSizeStrategy(bt.Strategy):
    '''Buys once and records the executed size and available cash before.'''
    def __init__(self):
        self.bought = False
        self.cash_before = None
        self.executed_size = None
        self.executed_price = None

    def next(self):
        if not self.bought:
            self.cash_before = self.broker.getcash()
            self.buy()
            self.bought = True

    def notify_order(self, order):
        if order.status == order.Completed and order.isbuy():
            self.executed_size = order.executed.size
            self.executed_price = order.executed.price


def _run(sizer_cls, cash=100000, **sizer_kwargs):
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(cash)
    cerebro.addstrategy(RecordSizeStrategy)
    cerebro.addsizer(sizer_cls, **sizer_kwargs)
    results = cerebro.run()
    return results[0]


# ---------------------------------------------------------------------------
# PercentSizer
# ---------------------------------------------------------------------------

def check_percent_sizer_uses_percent():
    '''PercentSizer should buy approximately percents% of available cash.'''
    pct = 50  # 50% of cash
    cash = 100000
    strat = _run(bt.sizers.PercentSizer, cash=cash, percents=pct)

    assert strat.executed_size is not None, 'Should have executed'
    assert strat.executed_price is not None

    expected_size = (cash * pct / 100) / strat.executed_price
    # Allow a small tolerance for integer truncation
    assert abs(strat.executed_size - expected_size) < 1.0, \
        'Size {} does not match expected {:.1f}'.format(
            strat.executed_size, expected_size)


def check_percent_sizer_default_twenty():
    '''Default percents is 20.'''
    cash = 100000
    strat_20 = _run(bt.sizers.PercentSizer, cash=cash)
    strat_custom = _run(bt.sizers.PercentSizer, cash=cash, percents=20)

    assert strat_20.executed_size == strat_custom.executed_size


def check_percent_sizer_different_percents():
    '''Higher percent should result in more shares bought.'''
    cash = 100000
    strat_20 = _run(bt.sizers.PercentSizer, cash=cash, percents=20)
    strat_80 = _run(bt.sizers.PercentSizer, cash=cash, percents=80)

    assert strat_80.executed_size > strat_20.executed_size, \
        '80% sizer should buy more than 20%'


def check_percent_sizer_int():
    '''PercentSizerInt should return an integer size.'''
    strat = _run(bt.sizers.PercentSizerInt, cash=100000, percents=50)
    assert strat.executed_size is not None
    assert strat.executed_size == int(strat.executed_size), \
        'PercentSizerInt should return integer size'


# ---------------------------------------------------------------------------
# AllInSizer
# ---------------------------------------------------------------------------

def check_allin_sizer():
    '''AllInSizer should use 100% of cash.'''
    cash = 100000
    strat_all = _run(bt.sizers.AllInSizer, cash=cash)
    strat_100 = _run(bt.sizers.PercentSizer, cash=cash, percents=100)

    assert strat_all.executed_size is not None
    # AllInSizer and PercentSizer at 100% should behave identically
    assert strat_all.executed_size == strat_100.executed_size, \
        'AllInSizer should match PercentSizer(percents=100)'


def check_allin_sizer_int():
    '''AllInSizerInt should return an integer.'''
    strat = _run(bt.sizers.AllInSizerInt, cash=100000)
    assert strat.executed_size is not None
    assert strat.executed_size == int(strat.executed_size)


def check_allin_uses_full_cash():
    '''AllInSizer should leave little cash remaining after buy.'''
    cash = 100000
    strat = _run(bt.sizers.AllInSizer, cash=cash)
    assert strat.executed_size is not None

    # Cash spent = size * price
    spent = strat.executed_size * strat.executed_price
    # Should have used most of the available cash
    assert spent / cash > 0.9, \
        'AllInSizer should use at least 90% of cash, used {:.1%}'.format(
            spent / cash)


# ---------------------------------------------------------------------------
# FixedSize (existing sizer — basic sanity check)
# ---------------------------------------------------------------------------

def check_fixed_size():
    strat = _run(bt.sizers.FixedSize, stake=5)
    assert strat.executed_size == 5


def check_fixed_size_tranches():
    '''FixedSize with tranches should divide stake.'''
    strat = _run(bt.sizers.FixedSize, stake=10, tranches=2)
    assert strat.executed_size == 5


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def test_run(main=False):
    check_percent_sizer_uses_percent()
    check_percent_sizer_default_twenty()
    check_percent_sizer_different_percents()
    check_percent_sizer_int()
    check_allin_sizer()
    check_allin_sizer_int()
    check_allin_uses_full_cash()
    check_fixed_size()
    check_fixed_size_tranches()

    if main:
        print('All sizer tests passed')


if __name__ == '__main__':
    test_run(main=True)
