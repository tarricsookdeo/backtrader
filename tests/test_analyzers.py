#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
'''Tests for all previously untested analyzers.'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime

import testcommon

import backtrader as bt


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class SMACrossStrategy(bt.Strategy):
    '''Simple SMA crossover to generate some trades.'''
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


def _run(analyzer_cls, cash=100000, strategy=None, **analyzer_kwargs):
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(cash)
    cerebro.addstrategy(strategy or SMACrossStrategy)
    cerebro.addanalyzer(analyzer_cls, **analyzer_kwargs)
    results = cerebro.run()
    strat = results[0]
    return strat.analyzers[0].get_analysis()


# ---------------------------------------------------------------------------
# SharpeRatio
# ---------------------------------------------------------------------------

def check_sharpe_ratio():
    analysis = _run(bt.analyzers.SharpeRatio)
    assert 'sharperatio' in analysis
    # sharperatio is a float or None — not empty
    sr = analysis['sharperatio']
    assert sr is None or isinstance(sr, float)


def check_sharpe_ratio_annualized():
    analysis = _run(bt.analyzers.SharpeRatio_A)
    assert 'sharperatio' in analysis


def check_sharpe_ratio_no_trades():
    '''SharpeRatio with a flat strategy should return None or a value.'''
    class FlatStrategy(bt.Strategy):
        def next(self):
            pass

    analysis = _run(bt.analyzers.SharpeRatio, strategy=FlatStrategy)
    assert 'sharperatio' in analysis


# ---------------------------------------------------------------------------
# TradeAnalyzer
# ---------------------------------------------------------------------------

def check_trade_analyzer_no_trades():
    class FlatStrategy(bt.Strategy):
        def next(self):
            pass

    analysis = _run(bt.analyzers.TradeAnalyzer, strategy=FlatStrategy)
    assert analysis.total.total == 0


def check_trade_analyzer_with_trades():
    analysis = _run(bt.analyzers.TradeAnalyzer)
    ta = analysis
    assert ta.total.total >= 0
    # If trades occurred, verify structure
    if ta.total.closed > 0:
        assert hasattr(ta.pnl.net, 'total')
        assert hasattr(ta.pnl.gross, 'total')
        assert hasattr(ta, 'won')
        assert hasattr(ta, 'lost')
        total_wl = ta.won.total + ta.lost.total
        assert total_wl == ta.total.closed


def check_trade_analyzer_long_short_counts():
    analysis = _run(bt.analyzers.TradeAnalyzer)
    ta = analysis
    if ta.total.closed > 0:
        assert ta.long.total + ta.short.total == ta.total.closed


# ---------------------------------------------------------------------------
# AnnualReturn
# ---------------------------------------------------------------------------

def check_annual_return():
    analysis = _run(bt.analyzers.AnnualReturn)
    # Should have at least one year key (2006 data)
    assert len(analysis) >= 1
    for year, ret in analysis.items():
        assert isinstance(year, int)
        assert isinstance(ret, float)


def check_annual_return_is_reasonable():
    analysis = _run(bt.analyzers.AnnualReturn)
    for year, ret in analysis.items():
        # Annual returns should be somewhat reasonable (not 1000x)
        assert -1.0 < ret < 10.0, \
            'Annual return {} for {} seems unreasonable'.format(ret, year)


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

def check_returns():
    analysis = _run(bt.analyzers.Returns)
    assert 'rtot' in analysis
    assert 'ravg' in analysis
    assert 'rnorm' in analysis
    assert 'rnorm100' in analysis
    assert isinstance(analysis['rtot'], float)
    # rnorm100 is rnorm * 100
    assert abs(analysis['rnorm100'] - analysis['rnorm'] * 100) < 1e-9


# ---------------------------------------------------------------------------
# Calmar
# ---------------------------------------------------------------------------

def check_calmar():
    # Need multiple years of data for Calmar; use the longer dataset
    cerebro = bt.Cerebro()
    import datetime
    data = bt.feeds.BacktraderCSVData(
        dataname=testcommon.modpath + '/../datas/2006-day-001.txt',
        fromdate=datetime.datetime(2006, 1, 1),
        todate=datetime.datetime(2006, 12, 31),
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.addstrategy(SMACrossStrategy)
    cerebro.addanalyzer(bt.analyzers.Calmar)
    results = cerebro.run()
    analysis = results[0].analyzers[0].get_analysis()
    # Calmar returns a dict keyed by datetime
    assert isinstance(analysis, dict)


# ---------------------------------------------------------------------------
# PositionsValue
# ---------------------------------------------------------------------------

def check_positions_value():
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.addstrategy(SMACrossStrategy)
    cerebro.addanalyzer(bt.analyzers.PositionsValue, cash=True)
    results = cerebro.run()
    analysis = results[0].analyzers[0].get_analysis()

    assert len(analysis) > 0
    # Each entry is a list with position value + cash
    for dt, vals in analysis.items():
        assert isinstance(vals, list)
        assert len(vals) >= 1  # at least the cash column


def check_positions_value_headers():
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.addstrategy(SMACrossStrategy)
    cerebro.addanalyzer(bt.analyzers.PositionsValue, headers=True, cash=True)
    results = cerebro.run()
    analysis = results[0].analyzers[0].get_analysis()

    # First entry should be a header row
    first_key = list(analysis.keys())[0]
    assert first_key == 'Datetime'


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def check_transactions():
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.addstrategy(SMACrossStrategy)
    cerebro.addanalyzer(bt.analyzers.Transactions)
    results = cerebro.run()
    analysis = results[0].analyzers[0].get_analysis()

    # Should have at least one transaction (SMA crossover will trade)
    assert len(analysis) > 0
    for dt, txns in analysis.items():
        assert isinstance(txns, list)
        for txn in txns:
            # [size, price, sid, symbol, value]
            assert len(txn) == 5
            size, price, sid, symbol, value = txn
            assert isinstance(size, (int, float))
            assert price > 0
            assert isinstance(symbol, str)


# ---------------------------------------------------------------------------
# GrossLeverage
# ---------------------------------------------------------------------------

def check_gross_leverage():
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.addstrategy(SMACrossStrategy)
    cerebro.addanalyzer(bt.analyzers.GrossLeverage)
    results = cerebro.run()
    analysis = results[0].analyzers[0].get_analysis()

    assert len(analysis) > 0
    for dt, leverage in analysis.items():
        assert leverage >= 0.0, 'Leverage should be non-negative'
        # Stock strategy: leverage should be <= 1 (no short selling or margin)
        assert leverage <= 1.0 + 1e-9, \
            'Long-only stock leverage should not exceed 1.0'


def check_gross_leverage_cash_only():
    '''With no positions, leverage should be 0.'''
    class FlatStrategy(bt.Strategy):
        def next(self):
            pass

    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.addstrategy(FlatStrategy)
    cerebro.addanalyzer(bt.analyzers.GrossLeverage)
    results = cerebro.run()
    analysis = results[0].analyzers[0].get_analysis()

    for dt, leverage in analysis.items():
        assert leverage == 0.0, \
            'No positions should give 0 leverage, got {}'.format(leverage)


# ---------------------------------------------------------------------------
# PeriodStats
# ---------------------------------------------------------------------------

def check_period_stats():
    analysis = _run(bt.analyzers.PeriodStats,
                    timeframe=bt.TimeFrame.Months)
    assert 'average' in analysis
    assert 'stddev' in analysis
    assert 'positive' in analysis
    assert 'negative' in analysis
    assert 'nochange' in analysis
    assert 'best' in analysis
    assert 'worst' in analysis

    total_periods = (analysis['positive'] + analysis['negative']
                     + analysis['nochange'])
    assert total_periods >= 1

    if total_periods > 1:
        assert analysis['best'] >= analysis['worst']


# ---------------------------------------------------------------------------
# VWR
# ---------------------------------------------------------------------------

def check_vwr():
    analysis = _run(bt.analyzers.VWR)
    assert 'vwr' in analysis
    assert isinstance(analysis['vwr'], float)


# ---------------------------------------------------------------------------
# LogReturnsRolling
# ---------------------------------------------------------------------------

def check_log_returns_rolling():
    cerebro = bt.Cerebro()
    data = testcommon.getdata(0)
    cerebro.adddata(data)
    cerebro.broker.setcash(100000)
    cerebro.addstrategy(SMACrossStrategy)
    cerebro.addanalyzer(bt.analyzers.LogReturnsRolling,
                        timeframe=bt.TimeFrame.Months)
    results = cerebro.run()
    analysis = results[0].analyzers[0].get_analysis()

    assert len(analysis) > 0
    for dt, ret in analysis.items():
        assert isinstance(ret, float)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def test_run(main=False):
    check_sharpe_ratio()
    check_sharpe_ratio_annualized()
    check_sharpe_ratio_no_trades()

    check_trade_analyzer_no_trades()
    check_trade_analyzer_with_trades()
    check_trade_analyzer_long_short_counts()

    check_annual_return()
    check_annual_return_is_reasonable()

    check_returns()

    check_calmar()

    check_positions_value()
    check_positions_value_headers()

    check_transactions()

    check_gross_leverage()
    check_gross_leverage_cash_only()

    check_period_stats()

    check_vwr()

    check_log_returns_rolling()

    if main:
        print('All analyzer tests passed')


if __name__ == '__main__':
    test_run(main=True)
