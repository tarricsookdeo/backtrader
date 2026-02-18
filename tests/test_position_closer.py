#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import os

import testcommon

import backtrader as bt
from backtrader.strategies.position_closer import EODPositionCloserMixin


modpath = os.path.dirname(os.path.abspath(__file__))


class BuyAndHoldStrategy(EODPositionCloserMixin, bt.Strategy):
    '''Buys once and holds. The mixin should close the position at close_time.'''
    params = (
        ('close_time', datetime.time(17, 0)),
        ('cancel_open_orders', True),
    )

    def __init__(self):
        super(BuyAndHoldStrategy, self).__init__()
        self.bought = False
        self.flat_after_close = []

    def next(self):
        if not self.bought and not self.position:
            self.buy()
            self.bought = True

        # Record whether we're flat after close_time
        bar_time = self.datetime.time()
        if bar_time > self.p.close_time:
            self.flat_after_close.append(self.position.size)

    def stop(self):
        # After close_time, position should be 0 (flat) on subsequent bars
        # Allow the first bar after close for the order to execute
        if len(self.flat_after_close) > 1:
            for size in self.flat_after_close[1:]:
                assert size == 0, \
                    'Position should be flat after close_time, got {}'.format(
                        size)


class MultipleBuysStrategy(EODPositionCloserMixin, bt.Strategy):
    '''Buys multiple times, verifying all get closed.'''
    params = (
        ('close_time', datetime.time(17, 0)),
        ('cancel_open_orders', True),
    )

    def __init__(self):
        super(MultipleBuysStrategy, self).__init__()
        self.buy_count = 0
        self.was_positioned = False
        self.was_flattened = False

    def next(self):
        bar_time = self.datetime.time()
        if bar_time < datetime.time(10, 0) and self.buy_count < 3:
            self.buy(size=1)
            self.buy_count += 1

        if self.position.size > 0:
            self.was_positioned = True

        if self.was_positioned and self.position.size == 0:
            self.was_flattened = True

    def stop(self):
        assert self.was_positioned, 'Should have had a position'
        assert self.was_flattened, 'Position should have been flattened by mixin'


def check_position_closed():
    '''Verify positions are closed after close_time.'''
    cerebro = bt.Cerebro()
    datapath = os.path.join(modpath, '..', 'datas', '2006-min-005.txt')
    data = bt.feeds.BacktraderCSVData(
        dataname=datapath,
        fromdate=datetime.datetime(2006, 1, 2),
        todate=datetime.datetime(2006, 1, 10),
    )
    cerebro.adddata(data)
    cerebro.addstrategy(BuyAndHoldStrategy)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def check_multiple_positions_closed():
    '''Verify multiple contracts are all closed.'''
    cerebro = bt.Cerebro()
    datapath = os.path.join(modpath, '..', 'datas', '2006-min-005.txt')
    data = bt.feeds.BacktraderCSVData(
        dataname=datapath,
        fromdate=datetime.datetime(2006, 1, 2),
        todate=datetime.datetime(2006, 1, 10),
    )
    cerebro.adddata(data)
    cerebro.addstrategy(MultipleBuysStrategy)
    cerebro.broker.setcash(1000000)
    cerebro.run()


def test_run(main=False):
    check_position_closed()
    check_multiple_positions_closed()

    if main:
        print('All EODPositionCloserMixin tests passed')


if __name__ == '__main__':
    test_run(main=True)
