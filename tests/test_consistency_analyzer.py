#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import os

import testcommon

import backtrader as bt
from backtrader.analyzers.consistency import ConsistencyAnalyzer


modpath = os.path.dirname(os.path.abspath(__file__))


def _run_with_strategy(strategy_cls, max_day_pct=40.0, cash=100000,
                       fromdate=None, todate=None):
    '''Run a cerebro with ConsistencyAnalyzer and return analyzer results.'''
    cerebro = bt.Cerebro()
    datapath = os.path.join(modpath, '..', 'datas', '2006-day-001.txt')
    data = bt.feeds.BacktraderCSVData(
        dataname=datapath,
        fromdate=fromdate or datetime.datetime(2006, 1, 1),
        todate=todate or datetime.datetime(2006, 12, 31),
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(cash)
    cerebro.addstrategy(strategy_cls)
    cerebro.addanalyzer(ConsistencyAnalyzer, max_day_pct=max_day_pct)
    results = cerebro.run()
    return results[0].analyzers[0].get_analysis()


class BuyAndSellStrategy(bt.Strategy):
    '''Buys on bar 1, sells on bar 2. Repeats every other bar.'''
    def __init__(self):
        self.bar = 0

    def next(self):
        self.bar += 1
        if self.bar % 2 == 1 and not self.position:
            self.buy(size=1)
        elif self.position:
            self.close()


class NeverTradesStrategy(bt.Strategy):
    '''Never places any orders — no trades should be recorded.'''
    def next(self):
        pass


class SingleTradeStrategy(bt.Strategy):
    '''Places exactly one round trip.'''
    def __init__(self):
        self.bought = False
        self.sold = False

    def next(self):
        if not self.bought and not self.position:
            self.buy(size=1)
            self.bought = True
        elif self.bought and not self.sold and self.position:
            self.close()
            self.sold = True


def check_no_trades():
    '''No trades -> daily_pnl empty, consistent=True, best_day=None.'''
    r = _run_with_strategy(NeverTradesStrategy)
    assert r.daily_pnl == {}, 'Expected empty daily_pnl'
    assert r.consistent is True
    assert r.best_day is None
    assert r.violations == []


def check_net_pnl_math():
    '''net_pnl should equal sum of daily_pnl values.'''
    r = _run_with_strategy(BuyAndSellStrategy)
    if not r.daily_pnl:
        return
    expected_net = sum(r.daily_pnl.values())
    assert abs(r.net_pnl - expected_net) < 1e-9, \
        'net_pnl mismatch: {} vs {}'.format(r.net_pnl, expected_net)


def check_total_profit_and_loss():
    '''total_profit and total_loss should correctly split daily P&L.'''
    r = _run_with_strategy(BuyAndSellStrategy)
    if not r.daily_pnl:
        return
    expected_profit = sum(v for v in r.daily_pnl.values() if v > 0)
    expected_loss = sum(v for v in r.daily_pnl.values() if v < 0)
    assert abs(r.total_profit - expected_profit) < 1e-9
    assert abs(r.total_loss - expected_loss) < 1e-9


def check_best_day_identified():
    '''best_day should be the day with the highest P&L.'''
    r = _run_with_strategy(BuyAndSellStrategy)
    if not r.daily_pnl or r.best_day is None:
        return
    best_pnl = max(r.daily_pnl.values())
    assert abs(r.best_day['pnl'] - best_pnl) < 1e-9, \
        'best_day pnl mismatch'
    assert r.best_day['date'] in r.daily_pnl


def check_no_violations_when_not_profitable():
    '''When net_pnl <= 0, violations list should be empty and consistent=True.'''
    # To force a loss, use a tiny cash amount so commissions dominate
    r = _run_with_strategy(BuyAndSellStrategy, cash=100)  # tiny account
    if r.net_pnl <= 0:
        assert r.violations == [], \
            'No violations should be flagged on a losing account'
        assert r.consistent is True


def check_consistent_when_all_days_under_threshold():
    '''No violations when all days are well below max_day_pct.'''
    r = _run_with_strategy(BuyAndSellStrategy, max_day_pct=100.0)
    # With 100% threshold, no single day can violate
    assert r.consistent is True
    assert r.violations == []


def check_violation_detected_with_low_threshold():
    '''With max_day_pct=0, every profitable day is a violation.'''
    r = _run_with_strategy(BuyAndSellStrategy, max_day_pct=0.0)
    if r.net_pnl > 0:
        # At least some profitable days should be flagged
        profitable_days = [d for d, v in r.daily_pnl.items() if v > 0]
        if profitable_days:
            assert not r.consistent, \
                'Should not be consistent when threshold is 0%'
            assert len(r.violations) > 0


def check_violation_pct_accuracy():
    '''Violation pct should equal day_pnl / net_pnl * 100.'''
    r = _run_with_strategy(BuyAndSellStrategy, max_day_pct=0.0)
    if not r.violations or r.net_pnl <= 0:
        return
    for v in r.violations:
        expected_pct = 100.0 * v['pnl'] / r.net_pnl
        assert abs(v['pct'] - expected_pct) < 1e-6, \
            'Violation pct incorrect: {} vs {}'.format(v['pct'], expected_pct)


def check_daily_pnl_keys_are_dates():
    '''Keys of daily_pnl should be date objects.'''
    r = _run_with_strategy(BuyAndSellStrategy)
    for key in r.daily_pnl:
        assert isinstance(key, datetime.date), \
            'daily_pnl keys should be date objects, got {}'.format(type(key))


def check_max_day_pct_in_results():
    '''max_day_pct in results should match the param.'''
    r = _run_with_strategy(BuyAndSellStrategy, max_day_pct=35.0)
    assert r.max_day_pct == 35.0


def test_run(main=False):
    check_no_trades()
    check_net_pnl_math()
    check_total_profit_and_loss()
    check_best_day_identified()
    check_no_violations_when_not_profitable()
    check_consistent_when_all_days_under_threshold()
    check_violation_detected_with_low_threshold()
    check_violation_pct_accuracy()
    check_daily_pnl_keys_are_dates()
    check_max_day_pct_in_results()

    if main:
        print('All ConsistencyAnalyzer tests passed')


if __name__ == '__main__':
    test_run(main=True)
