#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import os

import testcommon

import backtrader as bt
from backtrader.strategies.daily_loss_limit import DailyLossLimitMixin


modpath = os.path.dirname(os.path.abspath(__file__))


def _make_intraday_data(fromdate=None, todate=None):
    datapath = os.path.join(modpath, '..', 'datas', '2006-min-005.txt')
    return bt.feeds.BacktraderCSVData(
        dataname=datapath,
        fromdate=fromdate or datetime.datetime(2006, 1, 2),
        todate=todate or datetime.datetime(2006, 1, 10),
    )


def check_positions_closed_on_breach():
    '''When daily loss limit is hit, all positions should be closed.'''

    class BreachStrategy(DailyLossLimitMixin, bt.Strategy):
        params = (
            ('daily_loss_limit', 0.01),   # tiny limit — triggers immediately
            ('cancel_open_on_breach', True),
        )

        def __init__(self):
            super(BreachStrategy, self).__init__()
            self.bought = False
            self.position_closed_by_limit = False

        def next(self):
            if not self.bought and not self.position:
                self.buy(size=1)
                self.bought = True

            # Record when blocked and flat
            if self._trading_blocked and self.position.size == 0:
                self.position_closed_by_limit = True

            super(BreachStrategy, self).next()

        def stop(self):
            assert self.position_closed_by_limit, \
                'Position should have been closed when daily loss limit hit'

    cerebro = bt.Cerebro()
    cerebro.adddata(_make_intraday_data())
    cerebro.addstrategy(BreachStrategy)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_buy_blocked_after_breach():
    '''buy() should return None when _trading_blocked is True.'''

    class BlockCheckStrategy(DailyLossLimitMixin, bt.Strategy):
        params = (
            ('daily_loss_limit', 0.01),   # tiny limit — triggers on first loss
            ('cancel_open_on_breach', True),
        )

        def __init__(self):
            super(BlockCheckStrategy, self).__init__()
            self.blocked_buy_returned_none = False

        def next(self):
            if not self.position:
                self.buy(size=1)
            super(BlockCheckStrategy, self).next()

        def stop(self):
            # Directly verify the interception: set the flag and test buy()
            self._trading_blocked = True
            result = self.buy(size=1)
            assert result is None, \
                'buy() should return None when _trading_blocked is True'

    cerebro = bt.Cerebro()
    cerebro.adddata(_make_intraday_data())
    cerebro.addstrategy(BlockCheckStrategy)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_trading_resumes_next_day():
    '''Trading should be unblocked at the start of the next trading day.'''

    class DayResetStrategy(DailyLossLimitMixin, bt.Strategy):
        params = (
            ('daily_loss_limit', 0.01),   # triggers immediately on day 1
            ('cancel_open_on_breach', True),
        )

        def __init__(self):
            super(DayResetStrategy, self).__init__()
            self.first_day = None
            self.was_blocked = False
            self.was_unblocked_on_new_day = False

        def next(self):
            cur_date = self.datetime.date(0)

            if self.first_day is None:
                self.first_day = cur_date

            # Buy to create a position (mark-to-market will cause a loss)
            if not self.position and not self._trading_blocked:
                self.buy(size=1)

            if self._trading_blocked:
                self.was_blocked = True

            # On a day after the first, check if we're unblocked
            if self.was_blocked and cur_date != self.first_day:
                if not self._trading_blocked:
                    self.was_unblocked_on_new_day = True

            super(DayResetStrategy, self).next()

        def stop(self):
            assert self.was_blocked, \
                'Should have been blocked at some point'
            assert self.was_unblocked_on_new_day, \
                'Trading block should reset on a new trading day'

    cerebro = bt.Cerebro()
    cerebro.adddata(_make_intraday_data(
        fromdate=datetime.datetime(2006, 1, 2),
        todate=datetime.datetime(2006, 1, 6),
    ))
    cerebro.addstrategy(DayResetStrategy)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_no_breach_when_within_limit():
    '''No blocking when daily loss stays within the limit.'''

    class NoBreach(DailyLossLimitMixin, bt.Strategy):
        params = (
            ('daily_loss_limit', 999999999.0),   # impossibly high limit
            ('cancel_open_on_breach', True),
        )

        def __init__(self):
            super(NoBreach, self).__init__()
            self.ever_blocked = False

        def next(self):
            if self._trading_blocked:
                self.ever_blocked = True
            super(NoBreach, self).next()

        def stop(self):
            assert not self.ever_blocked, \
                'Should never have been blocked with impossibly high limit'

    cerebro = bt.Cerebro()
    cerebro.adddata(_make_intraday_data())
    cerebro.addstrategy(NoBreach)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_compatible_with_eod_closer():
    '''DailyLossLimitMixin should work alongside EODPositionCloserMixin.'''
    from backtrader.strategies.position_closer import EODPositionCloserMixin

    class ComboStrategy(DailyLossLimitMixin, EODPositionCloserMixin, bt.Strategy):
        params = (
            ('daily_loss_limit', 999999.0),
            ('cancel_open_on_breach', True),
            ('close_time', datetime.time(17, 0)),
            ('cancel_open_orders', True),
        )

        def __init__(self):
            super(ComboStrategy, self).__init__()
            self.bought = False

        def next(self):
            if not self.bought and not self.position:
                self.buy(size=1)
                self.bought = True
            super(ComboStrategy, self).next()

    cerebro = bt.Cerebro()
    cerebro.adddata(_make_intraday_data())
    cerebro.addstrategy(ComboStrategy)
    cerebro.broker.setcash(1000000)
    # Just verify it runs without error
    cerebro.run()


def test_run(main=False):
    check_positions_closed_on_breach()
    check_buy_blocked_after_breach()
    check_trading_resumes_next_day()
    check_no_breach_when_within_limit()
    check_compatible_with_eod_closer()

    if main:
        print('All DailyLossLimitMixin tests passed')


if __name__ == '__main__':
    test_run(main=True)
