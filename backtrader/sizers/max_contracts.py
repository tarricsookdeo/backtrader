#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt


class MaxContractsSizer(bt.Sizer):
    '''Sizer that enforces a maximum open position size per instrument.

    Returns ``stake`` contracts per order, but caps the size so the total
    position (existing + new) never exceeds ``max_contracts``. Applies
    independently per data feed.

    Params:

      - ``max_contracts`` (default: ``10``): maximum number of contracts
        that can be held at once (long or short)

      - ``stake`` (default: ``1``): number of contracts to request per order
    '''

    params = (
        ('max_contracts', 10),
        ('stake', 1),
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        position = self.strategy.getposition(data)
        current = position.size
        max_c = self.p.max_contracts
        desired = self.p.stake

        if isbuy:
            if current >= max_c:
                return 0
            available = max_c - current
            return min(desired, available)
        else:
            if current <= -max_c:
                return 0
            available = max_c + current
            return min(desired, available)
