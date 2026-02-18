#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
from backtrader.utils import AutoOrderedDict


__all__ = ['PropFirmDrawDown']


class PropFirmDrawDown(bt.Analyzer):
    '''Trailing drawdown analyzer for prop firm rule compliance.

    Tracks a high-water mark (HWM) and current drawdown from it. When the
    drawdown exceeds ``max_drawdown``, a breach event is recorded. Trading
    is **never** stopped — this is tracking only.

    Params:

      - ``max_drawdown`` (default: ``3000.0``): maximum allowed trailing
        drawdown in dollars before a breach is recorded

      - ``trailing_mode`` (default: ``'intraday'``): controls when the HWM
        is updated:

          - ``'intraday'``: HWM updates every bar
          - ``'eod'``: HWM only updates at end of day (detected by date
            change between bars; for daily data every bar is EOD)

      - ``trail_stop_threshold`` (default: ``None``): dollar profit level
        at which trailing stops. Once the account value reaches
        ``starting_balance + trail_stop_threshold``, the HWM is frozen at
        the threshold level (``starting_balance + trail_stop_threshold``),
        not the actual peak. After this, drawdown is measured from this
        frozen level.

      - ``starting_balance`` (default: ``None``): starting account balance.
        Auto-detected from the first bar if not set. Used to compute when
        ``trail_stop_threshold`` is reached.

      - ``fund`` (default: ``None``): if ``None``, autodetect fundmode
        from broker. Set ``True`` or ``False`` for explicit behavior.

    Methods:

      - ``get_analysis``: returns a dict with:

        - ``hwm`` — current high-water mark
        - ``current_value`` — latest portfolio value
        - ``current_drawdown`` — current drawdown in dollars from HWM
        - ``max_drawdown`` — largest drawdown seen in dollars
        - ``breached`` — True if max_drawdown limit was ever exceeded
        - ``breach_count`` — number of new-worst breach events
        - ``breaches`` — list of breach dicts (datetime, value, drawdown, hwm)
        - ``trailing_frozen`` — True if trailing has stopped
        - ``frozen_hwm`` — the frozen HWM value (None if not frozen)

      - ``is_breached()``: convenience method, returns True if breached
      - ``get_current_drawdown()``: returns current drawdown in dollars
    '''

    params = (
        ('max_drawdown', 3000.0),
        ('trailing_mode', 'intraday'),
        ('trail_stop_threshold', None),
        ('starting_balance', None),
        ('fund', None),
    )

    def start(self):
        super(PropFirmDrawDown, self).start()

        if self.p.fund is None:
            self._fundmode = self.strategy.broker.fundmode
        else:
            self._fundmode = self.p.fund

        self._current_value = 0.0
        self._hwm = float('-inf')
        self._trailing_frozen = False
        self._frozen_hwm = None
        self._starting_balance = self.p.starting_balance
        self._prev_date = None

        # Compute the absolute value target where trailing stops
        if (self._starting_balance is not None
                and self.p.trail_stop_threshold is not None):
            self._trail_target = (
                self._starting_balance + self.p.trail_stop_threshold)
        else:
            self._trail_target = None

    def create_analysis(self):
        self.rets = AutoOrderedDict()
        self.rets.hwm = 0.0
        self.rets.current_value = 0.0
        self.rets.current_drawdown = 0.0
        self.rets.max_drawdown = 0.0
        self.rets.breached = False
        self.rets.breach_count = 0
        self.rets.breaches = list()
        self.rets.trailing_frozen = False
        self.rets.frozen_hwm = None

    def notify_fund(self, cash, value, fundvalue, shares):
        if not self._fundmode:
            self._current_value = value
        else:
            self._current_value = fundvalue

        # Auto-detect starting balance on first call
        if self._starting_balance is None:
            self._starting_balance = self._current_value
            if self.p.trail_stop_threshold is not None:
                self._trail_target = (
                    self._starting_balance + self.p.trail_stop_threshold)

        # Initialize HWM on first call
        if self._hwm == float('-inf'):
            self._hwm = self._current_value

    def _update_hwm(self):
        '''Update the high-water mark, respecting the frozen state.'''
        if self._trailing_frozen:
            return

        if self._current_value > self._hwm:
            self._hwm = self._current_value

        # Check if trail_stop_threshold has been reached
        if (self._trail_target is not None
                and self._current_value >= self._trail_target
                and not self._trailing_frozen):
            self._trailing_frozen = True
            # Freeze HWM at the threshold level, not the actual peak
            self._hwm = self._trail_target
            self._frozen_hwm = self._trail_target

    def next(self):
        if self._hwm == float('-inf'):
            return  # not yet initialized

        # Update HWM based on trailing mode
        if self.p.trailing_mode == 'intraday':
            self._update_hwm()
        elif self.p.trailing_mode == 'eod':
            # Detect session end by date change
            cur_date = self.strategy.datetime.date(0)
            if self._prev_date is not None and cur_date != self._prev_date:
                # Date changed — previous bar was session end, update HWM
                # using the value that was current at that point
                self._update_hwm()
            self._prev_date = cur_date

        # Calculate current drawdown from HWM
        current_dd = max(0.0, self._hwm - self._current_value)

        r = self.rets
        r.hwm = self._hwm
        r.current_value = self._current_value
        r.current_drawdown = current_dd
        r.max_drawdown = max(r.max_drawdown, current_dd)
        r.trailing_frozen = self._trailing_frozen
        r.frozen_hwm = self._frozen_hwm

        # Check for breach
        if current_dd > self.p.max_drawdown:
            if not r.breached or current_dd > r.breaches[-1]['drawdown']:
                dt = self.strategy.datetime.datetime(0)
                r.breaches.append({
                    'datetime': dt,
                    'value': self._current_value,
                    'drawdown': current_dd,
                    'hwm': self._hwm,
                })
                r.breach_count = len(r.breaches)
            r.breached = True

    def stop(self):
        # For EOD mode, do a final HWM update for the last session
        if self.p.trailing_mode == 'eod':
            self._update_hwm()
            # Recalculate final drawdown
            if self._hwm != float('-inf'):
                current_dd = max(0.0, self._hwm - self._current_value)
                self.rets.current_drawdown = current_dd
                self.rets.max_drawdown = max(
                    self.rets.max_drawdown, current_dd)
                self.rets.hwm = self._hwm

        self.rets._close()

    def is_breached(self):
        '''Convenience method: returns True if max_drawdown was exceeded.'''
        return self.rets.breached

    def get_current_drawdown(self):
        '''Returns the current drawdown in dollars from HWM.'''
        return self.rets.current_drawdown
