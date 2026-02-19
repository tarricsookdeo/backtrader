#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
'''Tests for observers: Cash, Value, Broker, BuySell, DrawDown, Trades.'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import math

import testcommon

import backtrader as bt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SMACrossStrategy(bt.Strategy):
    params = (('period', 15),)

    def __init__(self):
        self.sma = bt.indicators.SMA(self.data, period=self.p.period)
        self.order = None

    def next(self):
        if self.order:
            return
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.order = self.buy()
        else:
            if self.data.close[0] < self.sma[0]:
                self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            self.order = None


class FlatStrategy(bt.Strategy):
    def next(self):
        pass


def _run(strategy, observers, cash=100000):
    cerebro = bt.Cerebro(stdstats=False)
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(cash)
    cerebro.addstrategy(strategy)
    for obs in observers:
        if isinstance(obs, tuple):
            cerebro.addobserver(obs[0], **obs[1])
        else:
            cerebro.addobserver(obs)
    return cerebro.run()[0]


def _isnan(v):
    try:
        return math.isnan(v)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Cash observer
# ---------------------------------------------------------------------------

def check_cash_observer():
    '''Cash observer should have a cash line with data.'''
    strat = _run(FlatStrategy, [bt.observers.Cash])
    obs = strat.observers[0]
    assert hasattr(obs.lines, 'cash')
    cash_line = obs.lines.cash
    assert len(cash_line) > 0
    for i in range(-len(cash_line), 0):
        if not _isnan(cash_line[i]):
            assert cash_line[i] > 0


def check_cash_observer_reflects_trades():
    '''Cash should decrease after a buy.'''
    class BuyOnceStrategy(bt.Strategy):
        def __init__(self):
            self.bought = False

        def next(self):
            if not self.bought:
                self.buy()
                self.bought = True

    strat = _run(BuyOnceStrategy, [bt.observers.Cash])
    obs = strat.observers[0]
    cash_line = obs.lines.cash
    # Find first and last non-NaN values
    values = [cash_line[i] for i in range(-len(cash_line), 0)
              if not _isnan(cash_line[i])]
    assert len(values) >= 2
    assert values[-1] < values[0], 'Cash should decrease after buying'


# ---------------------------------------------------------------------------
# Value observer
# ---------------------------------------------------------------------------

def check_value_observer():
    '''Value observer should track portfolio value.'''
    strat = _run(FlatStrategy, [bt.observers.Value])
    obs = strat.observers[0]
    assert hasattr(obs.lines, 'value')
    value_line = obs.lines.value
    assert len(value_line) > 0
    for i in range(-len(value_line), 0):
        if not _isnan(value_line[i]):
            assert abs(value_line[i] - 100000.0) < 1.0


# ---------------------------------------------------------------------------
# Broker (CashValue) observer
# ---------------------------------------------------------------------------

def check_broker_observer():
    '''Broker observer tracks both cash and value.'''
    strat = _run(FlatStrategy, [bt.observers.Broker])
    obs = strat.observers[0]
    assert hasattr(obs.lines, 'cash')
    assert hasattr(obs.lines, 'value')
    cash_line = obs.lines.cash
    value_line = obs.lines.value
    for i in range(-len(cash_line), 0):
        if not _isnan(cash_line[i]) and not _isnan(value_line[i]):
            assert abs(cash_line[i] - value_line[i]) < 1e-6


# ---------------------------------------------------------------------------
# BuySell observer
# ---------------------------------------------------------------------------

def check_buysell_observer_has_lines():
    strat = _run(SMACrossStrategy, [bt.observers.BuySell])
    obs = strat.observers[0]
    assert hasattr(obs.lines, 'buy')
    assert hasattr(obs.lines, 'sell')


def check_buysell_observer_records_buys():
    '''BuySell should record at least one buy price.'''
    strat = _run(SMACrossStrategy, [bt.observers.BuySell])
    obs = strat.observers[0]
    buy_line = obs.lines.buy
    has_buy = any(
        not _isnan(buy_line[i]) and buy_line[i] > 0
        for i in range(-len(buy_line), 0)
    )
    assert has_buy, 'BuySell should have recorded at least one buy'


def check_buysell_barplot_mode():
    strat = _run(SMACrossStrategy,
                 [(bt.observers.BuySell, {'barplot': True})])
    obs = strat.observers[0]
    assert hasattr(obs.lines, 'buy')
    assert hasattr(obs.lines, 'sell')


# ---------------------------------------------------------------------------
# DrawDown observer
# ---------------------------------------------------------------------------

def check_drawdown_observer_has_lines():
    strat = _run(SMACrossStrategy, [bt.observers.DrawDown])
    obs = strat.observers[0]
    assert hasattr(obs.lines, 'drawdown')
    assert hasattr(obs.lines, 'maxdrawdown')


def check_drawdown_observer_non_negative():
    strat = _run(SMACrossStrategy, [bt.observers.DrawDown])
    obs = strat.observers[0]
    dd_line = obs.lines.drawdown
    for i in range(-len(dd_line), 0):
        val = dd_line[i]
        if not _isnan(val):
            assert val >= 0, 'Drawdown should be non-negative: {}'.format(val)


def check_maxdrawdown_gte_drawdown():
    strat = _run(SMACrossStrategy, [bt.observers.DrawDown])
    obs = strat.observers[0]
    dd = obs.lines.drawdown
    maxdd = obs.lines.maxdrawdown
    for i in range(-len(dd), 0):
        if not _isnan(dd[i]) and not _isnan(maxdd[i]):
            assert maxdd[i] >= dd[i] - 1e-9


# ---------------------------------------------------------------------------
# Trades observer
# ---------------------------------------------------------------------------

def check_trades_observer_has_lines():
    strat = _run(SMACrossStrategy, [bt.observers.Trades])
    obs = strat.observers[0]
    assert hasattr(obs.lines, 'pnlplus')
    assert hasattr(obs.lines, 'pnlminus')


def check_trades_pnlplus_non_negative():
    strat = _run(SMACrossStrategy, [bt.observers.Trades])
    obs = strat.observers[0]
    pnlplus = obs.lines.pnlplus
    for i in range(-len(pnlplus), 0):
        val = pnlplus[i]
        if not _isnan(val) and val != 0.0:
            assert val >= 0, 'pnlplus should be >= 0: {}'.format(val)


def check_trades_pnlminus_non_positive():
    strat = _run(SMACrossStrategy, [bt.observers.Trades])
    obs = strat.observers[0]
    pnlminus = obs.lines.pnlminus
    for i in range(-len(pnlminus), 0):
        val = pnlminus[i]
        if not _isnan(val) and val != 0.0:
            assert val <= 0, 'pnlminus should be <= 0: {}'.format(val)


# ---------------------------------------------------------------------------
# Multiple observers together
# ---------------------------------------------------------------------------

def check_multiple_observers_coexist():
    strat = _run(SMACrossStrategy, [
        bt.observers.Cash,
        bt.observers.Value,
        bt.observers.BuySell,
        bt.observers.DrawDown,
        bt.observers.Trades,
    ])
    assert len(strat.observers) == 5


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def test_run(main=False):
    check_cash_observer()
    check_cash_observer_reflects_trades()
    check_value_observer()
    check_broker_observer()
    check_buysell_observer_has_lines()
    check_buysell_observer_records_buys()
    check_buysell_barplot_mode()
    check_drawdown_observer_has_lines()
    check_drawdown_observer_non_negative()
    check_maxdrawdown_gte_drawdown()
    check_trades_observer_has_lines()
    check_trades_pnlplus_non_negative()
    check_trades_pnlminus_non_positive()
    check_multiple_observers_coexist()

    if main:
        print('All observer tests passed')


if __name__ == '__main__':
    test_run(main=True)
