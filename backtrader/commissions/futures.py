#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from . import CommInfo_Futures_Fixed


class FuturesCommInfo(CommInfo_Futures_Fixed):
    '''Futures commission info with explicit tick size/value configuration.

    Auto-derives ``mult`` from ``tick_value / tick_size`` so P&L is
    calculated correctly without manual multiplier math.

    Params:

      - ``tick_size`` (def: ``0.25``): minimum price increment
      - ``tick_value`` (def: ``12.50``): dollar value per tick per contract
      - ``margin``: margin per contract in dollars
      - ``commission`` (def: ``0.0``): fixed commission per contract per side
    '''

    params = (
        ('tick_size', 0.25),
        ('tick_value', 12.50),
    )

    def __init__(self):
        if self.p.tick_size <= 0:
            raise ValueError(
                'tick_size must be positive, got {}'.format(self.p.tick_size))
        self.p.mult = self.p.tick_value / self.p.tick_size
        super(FuturesCommInfo, self).__init__()


class ESFuturesCommInfo(FuturesCommInfo):
    '''E-mini S&P 500 (ES)'''
    params = (
        ('tick_size', 0.25),
        ('tick_value', 12.50),
        ('margin', 15000.0),
        ('commission', 2.25),
    )


class NQFuturesCommInfo(FuturesCommInfo):
    '''E-mini Nasdaq 100 (NQ)'''
    params = (
        ('tick_size', 0.25),
        ('tick_value', 5.0),
        ('margin', 20000.0),
        ('commission', 2.25),
    )


class CLFuturesCommInfo(FuturesCommInfo):
    '''Crude Oil (CL)'''
    params = (
        ('tick_size', 0.01),
        ('tick_value', 10.0),
        ('margin', 5000.0),
        ('commission', 2.25),
    )


class MESFuturesCommInfo(FuturesCommInfo):
    '''Micro E-mini S&P 500 (MES)'''
    params = (
        ('tick_size', 0.25),
        ('tick_value', 1.25),
        ('margin', 1500.0),
        ('commission', 0.50),
    )


class MNQFuturesCommInfo(FuturesCommInfo):
    '''Micro E-mini Nasdaq 100 (MNQ)'''
    params = (
        ('tick_size', 0.25),
        ('tick_value', 0.50),
        ('margin', 2000.0),
        ('commission', 0.50),
    )
