#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
from backtrader.utils import AutoOrderedDict


__all__ = ['ConsistencyAnalyzer']


class ConsistencyAnalyzer(bt.Analyzer):
    '''Prop firm consistency rule analyzer.

    Many prop firms require that no single trading day contributes more
    than a fixed percentage of total net profit (e.g. 40%). This analyzer
    tracks daily closed P&L and flags any violations.

    Violations are only computed when total net P&L is positive — if the
    account is overall at a loss there is no consistency threshold to enforce.

    Params:

      - ``max_day_pct`` (default: ``40.0``): maximum percentage of total
        net profit that any single profitable day may represent

    Methods:

      - ``get_analysis``: returns a dict with:

        - ``daily_pnl`` — dict mapping each trading date to its net P&L
          (sum of closed trade net P&L for that day)
        - ``net_pnl`` — total net P&L across all days
        - ``total_profit`` — sum of all positive-day P&Ls
        - ``total_loss`` — sum of all negative-day P&Ls
        - ``consistent`` — True if no violations were found
        - ``max_day_pct`` — the param value used for reference
        - ``best_day`` — dict with ``date``, ``pnl``, ``pct`` for the
          highest P&L day; None if no trades closed
        - ``violations`` — list of dicts (``date``, ``pnl``, ``pct``) for
          days that exceeded the consistency threshold
    '''

    params = (
        ('max_day_pct', 40.0),
    )

    def start(self):
        super(ConsistencyAnalyzer, self).start()
        self._daily_pnl = {}

    def create_analysis(self):
        self.rets = AutoOrderedDict()
        self.rets.daily_pnl = {}
        self.rets.net_pnl = 0.0
        self.rets.total_profit = 0.0
        self.rets.total_loss = 0.0
        self.rets.consistent = True
        self.rets.max_day_pct = self.p.max_day_pct
        self.rets.best_day = None
        self.rets.violations = []

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        cur_date = self.strategy.datetime.date(0)
        prev = self._daily_pnl.get(cur_date, 0.0)
        self._daily_pnl[cur_date] = prev + trade.pnlcomm

    def stop(self):
        r = self.rets
        r.daily_pnl = self._daily_pnl

        if not self._daily_pnl:
            r._close()
            return

        r.net_pnl = sum(self._daily_pnl.values())
        r.total_profit = sum(v for v in self._daily_pnl.values() if v > 0)
        r.total_loss = sum(v for v in self._daily_pnl.values() if v < 0)

        # Best day by P&L
        best_date = max(self._daily_pnl, key=lambda d: self._daily_pnl[d])
        best_pnl = self._daily_pnl[best_date]
        best_pct = (
            100.0 * best_pnl / r.net_pnl if r.net_pnl > 0 else 0.0)
        r.best_day = {
            'date': best_date,
            'pnl': best_pnl,
            'pct': best_pct,
        }

        # Violations only apply when net P&L is positive
        if r.net_pnl > 0:
            violations = []
            for date, pnl in self._daily_pnl.items():
                if pnl <= 0:
                    continue
                pct = 100.0 * pnl / r.net_pnl
                if pct > self.p.max_day_pct:
                    violations.append({
                        'date': date,
                        'pnl': pnl,
                        'pct': pct,
                    })
            r.violations = violations
            r.consistent = len(violations) == 0
        else:
            r.consistent = True  # not applicable when not profitable

        r._close()
