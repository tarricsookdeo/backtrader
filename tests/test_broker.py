#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
'''Tests for broker order execution, margin, and mark-to-market.'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import os

import testcommon

import backtrader as bt


modpath = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cerebro(cash=100000):
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(cash)
    return cerebro


def _run(strategy, cash=100000, **kwargs):
    cerebro = _cerebro(cash)
    cerebro.addstrategy(strategy, **kwargs)
    return cerebro.run()[0], cerebro.broker


# ---------------------------------------------------------------------------
# Market order
# ---------------------------------------------------------------------------

class MarketBuyStrategy(bt.Strategy):
    def __init__(self):
        self.bought = False
        self.buy_price = None

    def next(self):
        if not self.bought:
            self.buy()
            self.bought = True

    def notify_order(self, order):
        if order.status == order.Completed and order.isbuy():
            self.buy_price = order.executed.price


def check_market_order_executes():
    strat, broker = _run(MarketBuyStrategy)
    assert strat.buy_price is not None, 'Market buy should have executed'
    assert strat.buy_price > 0
    assert broker.getposition(strat.data).size == 1


# ---------------------------------------------------------------------------
# Limit order — hit and miss
# ---------------------------------------------------------------------------

class LimitHitStrategy(bt.Strategy):
    params = (('limit_price', None),)

    def __init__(self):
        self.placed = False
        self.executed = False

    def next(self):
        if not self.placed:
            # Place limit well above current price — should always fill
            price = self.data.high[0] * 2.0
            self.buy(exectype=bt.Order.Limit, price=price)
            self.placed = True

    def notify_order(self, order):
        if order.status == order.Completed:
            self.executed = True


class LimitMissStrategy(bt.Strategy):
    def __init__(self):
        self.placed = False
        self.executed = False
        self.expired = False

    def next(self):
        if not self.placed:
            # Limit price at 1 cent — will never hit
            self.buy(exectype=bt.Order.Limit, price=0.01, valid=1)
            self.placed = True

    def notify_order(self, order):
        if order.status == order.Completed:
            self.executed = True
        elif order.status == order.Expired:
            self.expired = True


def check_limit_order_hits():
    strat, broker = _run(LimitHitStrategy)
    assert strat.executed, 'Limit order above market should fill'


def check_limit_order_misses():
    strat, broker = _run(LimitMissStrategy)
    assert not strat.executed, 'Limit order at $0.01 should not fill'
    assert strat.expired, 'Order should have expired'


# ---------------------------------------------------------------------------
# Stop order
# ---------------------------------------------------------------------------

class StopOrderStrategy(bt.Strategy):
    def __init__(self):
        self.placed = False
        self.executed = False
        self.stop_price = None

    def next(self):
        if not self.placed:
            # Stop price above current close — triggers when price rises
            stop = self.data.close[0] * 1.001
            self.buy(exectype=bt.Order.Stop, price=stop)
            self.placed = True

    def notify_order(self, order):
        if order.status == order.Completed:
            self.executed = True
            self.stop_price = order.executed.price


def check_stop_order_triggers():
    strat, broker = _run(StopOrderStrategy)
    # Stop just above market — will trigger on price movement
    assert strat.executed, 'Stop order near market should eventually trigger'
    assert strat.stop_price > 0


# ---------------------------------------------------------------------------
# Order cancellation
# ---------------------------------------------------------------------------

class CancelOrderStrategy(bt.Strategy):
    def __init__(self):
        self.order = None
        self.cancelled = False
        self.executed = False

    def next(self):
        if self.order is None:
            # Limit at $1 — will never fill
            self.order = self.buy(exectype=bt.Order.Limit, price=0.01)
        elif not self.cancelled:
            self.cancel(self.order)
            self.cancelled = True

    def notify_order(self, order):
        if order.status == order.Canceled:
            self.cancelled = True
        if order.status == order.Completed:
            self.executed = True


def check_cancel_order():
    strat, broker = _run(CancelOrderStrategy)
    assert strat.cancelled, 'Order should be cancelled'
    assert not strat.executed, 'Cancelled order should not execute'


# ---------------------------------------------------------------------------
# Margin rejection
# ---------------------------------------------------------------------------

class MarginRejectionStrategy(bt.Strategy):
    '''Tries to buy way more than cash allows.'''
    def __init__(self):
        self.rejected = False
        self.placed = False

    def next(self):
        if not self.placed:
            # Try to buy 1,000,000 shares at market price — impossible
            self.buy(size=1000000)
            self.placed = True

    def notify_order(self, order):
        if order.status == order.Margin:
            self.rejected = True


def check_margin_rejection():
    strat, broker = _run(MarginRejectionStrategy, cash=100)
    assert strat.rejected, 'Order should be rejected due to insufficient margin'


# ---------------------------------------------------------------------------
# Position tracking
# ---------------------------------------------------------------------------

class PositionTrackingStrategy(bt.Strategy):
    def __init__(self):
        self.sizes = []
        self.bought = False
        self.sold = False

    def next(self):
        if not self.bought:
            self.buy(size=2)
            self.bought = True
        elif self.position.size == 2 and not self.sold:
            self.sell(size=1)
            self.sold = True

        self.sizes.append(self.position.size)

    def stop(self):
        assert 2 in self.sizes, 'Position should have reached 2'
        assert 1 in self.sizes, 'Position should have reduced to 1'


def check_position_tracking():
    _run(PositionTrackingStrategy)


# ---------------------------------------------------------------------------
# Short selling
# ---------------------------------------------------------------------------

class ShortSellingStrategy(bt.Strategy):
    def __init__(self):
        self.short_placed = False
        self.min_position = 0

    def next(self):
        if not self.short_placed:
            self.sell(size=1)
            self.short_placed = True
        pos = self.position.size
        if pos < self.min_position:
            self.min_position = pos

    def stop(self):
        assert self.min_position < 0, 'Should have had a short position'


def check_short_selling():
    _run(ShortSellingStrategy, cash=1000000)


# ---------------------------------------------------------------------------
# Futures mark-to-market (cashadjust)
# ---------------------------------------------------------------------------

class FuturesMTMStrategy(bt.Strategy):
    def __init__(self):
        self.bought = False
        self.cash_after_buy = None
        self.cash_next_bar = None

    def next(self):
        if not self.bought:
            self.buy(size=1)
            self.bought = True
        elif self.cash_after_buy is None and self.position.size == 1:
            self.cash_after_buy = self.broker.getcash()
        elif (self.cash_after_buy is not None
              and self.cash_next_bar is None):
            self.cash_next_bar = self.broker.getcash()


def check_futures_mark_to_market():
    '''Futures cash should change each bar due to daily settlement.'''
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(1000000)
    # Set up futures-style commission (mult, margin)
    cerebro.broker.setcommission(mult=10.0, margin=1000.0, commission=0.0)
    cerebro.addstrategy(FuturesMTMStrategy)

    results = cerebro.run()
    strat = results[0]

    assert strat.cash_after_buy is not None
    assert strat.cash_next_bar is not None
    # Cash should have changed between bars due to mark-to-market
    assert strat.cash_after_buy != strat.cash_next_bar, \
        'Futures cash should change each bar due to mark-to-market'


# ---------------------------------------------------------------------------
# Bracket order
# ---------------------------------------------------------------------------

class BracketOrderStrategy(bt.Strategy):
    def __init__(self):
        self.placed = False
        self.main_executed = False
        self.stop_status = None
        self.limit_status = None

    def next(self):
        if not self.placed:
            price = self.data.close[0]
            self.buy_bracket(
                price=price * 2.0,          # limit entry (well above, fills)
                exectype=bt.Order.Limit,
                stopprice=price * 0.5,      # stop-loss
                limitprice=price * 3.0,     # take-profit
            )
            self.placed = True

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.main_executed = True
        if order.status in [order.Canceled, order.Completed, order.Expired]:
            if not order.isbuy():
                if self.stop_status is None:
                    self.stop_status = order.status
                else:
                    self.limit_status = order.status


def check_bracket_order():
    strat, broker = _run(BracketOrderStrategy)
    assert strat.main_executed, 'Main bracket order should execute'


# ---------------------------------------------------------------------------
# Cash management
# ---------------------------------------------------------------------------

def check_setcash():
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(12345.0)
    assert cerebro.broker.getcash() == 12345.0


def check_add_cash():
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    data = testcommon.getdata(0)
    cerebro.adddata(data)

    class AddCashStrategy(bt.Strategy):
        def __init__(self):
            self.cash_before = None
            self.cash_after = None
            self.bar = 0

        def next(self):
            self.bar += 1
            if self.bar == 1:
                self.cash_before = self.broker.getcash()
                self.broker.add_cash(5000.0)
            elif self.bar == 2:
                # Cash addition is processed between bars
                self.cash_after = self.broker.getcash()

        def stop(self):
            assert self.cash_after is not None
            assert self.cash_after == self.cash_before + 5000.0, \
                'Expected {} got {}'.format(
                    self.cash_before + 5000.0, self.cash_after)

    cerebro.addstrategy(AddCashStrategy)
    cerebro.run()


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def test_run(main=False):
    check_market_order_executes()
    check_limit_order_hits()
    check_limit_order_misses()
    check_stop_order_triggers()
    check_cancel_order()
    check_margin_rejection()
    check_position_tracking()
    check_short_selling()
    check_futures_mark_to_market()
    check_bracket_order()
    check_setcash()
    check_add_cash()

    if main:
        print('All broker tests passed')


if __name__ == '__main__':
    test_run(main=True)
