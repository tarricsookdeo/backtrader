#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


_DEFAULT_DAILY_LOSS_LIMIT = 1000.0
_DEFAULT_CANCEL_OPEN = True


class DailyLossLimitMixin(object):
    '''Strategy mixin that enforces a maximum intraday dollar loss limit.

    When the portfolio value drops ``daily_loss_limit`` dollars from its
    value at the start of the trading day, all open positions are closed
    and all new buy/sell orders are blocked for the remainder of that day.
    Trading resumes automatically at the start of the next trading day.

    Add this mixin **before** ``bt.Strategy`` in the inheritance chain and
    define the params on your strategy class::

        class MyStrategy(DailyLossLimitMixin, bt.Strategy):
            params = (
                ('daily_loss_limit', 1000.0),
                ('cancel_open_on_breach', True),
            )

    Params (define on your strategy):

      - ``daily_loss_limit`` (default: ``1000.0``): maximum intraday dollar
        loss allowed before trading is halted for the day

      - ``cancel_open_on_breach`` (default: ``True``): if True, all pending
        orders are cancelled when the daily loss limit is hit

    Accessible attributes:

      - ``_trading_blocked``: True if the daily loss limit has been hit
        for the current day

      - ``_day_start_value``: portfolio value at the start of the current
        trading day

    Note:
      The ``buy()`` and ``sell()`` methods are intercepted by this mixin.
      When ``_trading_blocked`` is True, they return ``None`` silently
      instead of placing orders.
    '''

    def __init__(self):
        super(DailyLossLimitMixin, self).__init__()
        self._day_start_value = 0.0
        self._trading_blocked = False
        self._bypass_block = False
        self._prev_date = None

    def start(self):
        super(DailyLossLimitMixin, self).start()
        self._day_start_value = self.broker.getvalue()
        self._trading_blocked = False
        self._bypass_block = False
        self._prev_date = None

    def notify_cashvalue(self, cash, value):
        '''Detects day changes and resets trading block for new sessions.

        Called BEFORE next() each bar, ensuring the block is correctly
        reset before the user's trading logic runs on the first bar of
        a new trading day.
        '''
        cur_date = self.datetime.date(0)
        if self._prev_date is not None and cur_date != self._prev_date:
            # New trading day — reset state
            self._day_start_value = value
            self._trading_blocked = False
        self._prev_date = cur_date
        super(DailyLossLimitMixin, self).notify_cashvalue(cash, value)

    def next(self):
        if not self._trading_blocked:
            daily_loss = self._day_start_value - self.broker.getvalue()
            limit = getattr(
                self.p, 'daily_loss_limit', _DEFAULT_DAILY_LOSS_LIMIT)
            if daily_loss >= limit:
                self._trading_blocked = True
                cancel = getattr(
                    self.p, 'cancel_open_on_breach', _DEFAULT_CANCEL_OPEN)
                if cancel:
                    self._cancel_all_open_orders()
                self._flatten_all_positions()
        super(DailyLossLimitMixin, self).next()

    def buy(self, *args, **kwargs):
        if self._trading_blocked and not self._bypass_block:
            return None
        return super(DailyLossLimitMixin, self).buy(*args, **kwargs)

    def sell(self, *args, **kwargs):
        if self._trading_blocked and not self._bypass_block:
            return None
        return super(DailyLossLimitMixin, self).sell(*args, **kwargs)

    def _flatten_all_positions(self):
        '''Close all open positions, bypassing the trading block.'''
        self._bypass_block = True
        try:
            for data in self.datas:
                pos = self.broker.getposition(data)
                if pos.size != 0:
                    self.close(data=data)
        finally:
            self._bypass_block = False

    def _cancel_all_open_orders(self):
        '''Cancel all pending orders.'''
        for order in self.broker.get_orders_open(safe=True):
            self.cancel(order)
