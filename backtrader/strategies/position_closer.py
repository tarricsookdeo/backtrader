#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime


_DEFAULT_CLOSE_TIME = datetime.time(15, 55)
_DEFAULT_CANCEL_OPEN = True


class EODPositionCloserMixin(object):
    '''Strategy mixin that closes all positions at a configurable time.

    Uses the backtrader timer system to fire at ``close_time`` each session.
    When triggered, cancels all open orders and flattens every position.

    Add this mixin **before** ``bt.Strategy`` in the inheritance chain and
    define the params on your strategy class::

        class MyStrategy(EODPositionCloserMixin, bt.Strategy):
            params = (
                ('close_time', datetime.time(15, 55)),
                ('cancel_open_orders', True),
            )

    Params (define on your strategy):

      - ``close_time`` (default: ``datetime.time(15, 55)``): time at which
        all positions are closed via market order

      - ``cancel_open_orders`` (default: ``True``): if True, all pending
        orders are cancelled before closing positions
    '''

    def __init__(self):
        super(EODPositionCloserMixin, self).__init__()
        self._eod_timer = None

    def start(self):
        super(EODPositionCloserMixin, self).start()
        close_time = getattr(self.p, 'close_time', _DEFAULT_CLOSE_TIME)
        self._eod_timer = self.add_timer(when=close_time)

    def notify_timer(self, timer, when, *args, **kwargs):
        if timer is self._eod_timer:
            self._close_all_positions()

        super(EODPositionCloserMixin, self).notify_timer(
            timer, when, *args, **kwargs)

    def _close_all_positions(self):
        cancel = getattr(self.p, 'cancel_open_orders', _DEFAULT_CANCEL_OPEN)
        if cancel:
            for order in self.broker.get_orders_open(safe=True):
                self.cancel(order)

        for data in self.datas:
            pos = self.broker.getposition(data)
            if pos.size != 0:
                self.close(data=data)
