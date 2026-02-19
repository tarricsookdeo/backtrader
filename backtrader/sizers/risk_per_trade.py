#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt


__all__ = ['RiskPerTradeSizer']


class RiskPerTradeSizer(bt.Sizer):
    '''Sizer that sizes positions based on a fixed dollar risk per trade.

    Computes position size as::

        size = floor(risk_per_trade / (stop_ticks * tick_value))

    where ``tick_value`` is the dollar gain/loss per tick per contract.
    When used with ``FuturesCommInfo``, ``tick_value`` is auto-detected
    from the commission info; otherwise it must be set explicitly.

    Params:

      - ``risk_per_trade`` (default: ``100.0``): maximum dollar loss
        acceptable if the stop is hit

      - ``stop_ticks`` (default: ``4``): number of ticks between the entry
        price and the stop loss level

      - ``tick_value`` (default: ``None``): dollar value per tick per
        contract. Auto-detected from ``comminfo.p.tick_value`` when using
        ``FuturesCommInfo``. Must be set explicitly for other commission
        types.
    '''

    params = (
        ('risk_per_trade', 100.0),
        ('stop_ticks', 4),
        ('tick_value', None),
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        if self.p.stop_ticks <= 0:
            raise ValueError(
                'stop_ticks must be positive, got {}'.format(self.p.stop_ticks))

        if self.p.tick_value is not None:
            tick_value = self.p.tick_value
        elif hasattr(comminfo.p, 'tick_value'):
            tick_value = comminfo.p.tick_value
        else:
            raise ValueError(
                'tick_value param must be set for non-FuturesCommInfo '
                'instruments (comminfo has no tick_value attribute)')

        size = int(self.p.risk_per_trade / (self.p.stop_ticks * tick_value))
        return max(0, size)
