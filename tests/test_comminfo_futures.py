#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import testcommon

import backtrader as bt
from backtrader import Position
from backtrader.commissions.futures import (
    FuturesCommInfo,
    ESFuturesCommInfo,
    NQFuturesCommInfo,
    CLFuturesCommInfo,
    MESFuturesCommInfo,
    MNQFuturesCommInfo,
)


def check_mult_derivation():
    '''mult should be auto-derived from tick_value / tick_size'''
    comm = FuturesCommInfo(tick_size=0.25, tick_value=12.50, margin=15000)
    assert comm.p.mult == 50.0

    comm2 = FuturesCommInfo(tick_size=0.01, tick_value=10.0, margin=5000)
    assert comm2.p.mult == 1000.0

    comm3 = FuturesCommInfo(tick_size=0.25, tick_value=0.50, margin=2000)
    assert comm3.p.mult == 2.0


def check_invalid_tick_size():
    '''tick_size <= 0 should raise ValueError'''
    try:
        FuturesCommInfo(tick_size=0, tick_value=12.50, margin=15000)
        assert False, 'Should have raised ValueError'
    except ValueError:
        pass

    try:
        FuturesCommInfo(tick_size=-1, tick_value=12.50, margin=15000)
        assert False, 'Should have raised ValueError'
    except ValueError:
        pass


def check_pnl():
    '''P&L should equal size * price_change * mult'''
    # ES: tick_size=0.25, tick_value=12.50 -> mult=50
    comm = ESFuturesCommInfo()
    size = 2
    entry = 5000.0
    exit = 5010.0

    pnl = comm.profitandloss(size, entry, exit)
    # 2 contracts * (5010 - 5000) * 50 = 1000
    assert pnl == 1000.0

    # Losing trade
    pnl_loss = comm.profitandloss(size, entry, 4990.0)
    # 2 * (4990 - 5000) * 50 = -1000
    assert pnl_loss == -1000.0


def check_cash_adjust():
    '''Mark-to-market cash adjustment for futures'''
    comm = ESFuturesCommInfo()
    size = 1
    price = 5000.0
    newprice = 5001.0

    ca = comm.cashadjust(size, price, newprice)
    # 1 * (5001 - 5000) * 50 = 50
    assert ca == 50.0


def check_commission():
    '''Commission should be fixed per contract'''
    comm = ESFuturesCommInfo()
    size = 3

    cost = comm.getcommission(size, 5000.0)
    # 3 * 2.25 = 6.75
    assert cost == 6.75


def check_margin():
    '''Margin should be fixed per contract'''
    comm = ESFuturesCommInfo()
    pos = Position(size=2, price=5000.0)
    value = comm.getvalue(pos, 5000.0)
    # 2 * 15000 = 30000
    assert value == 30000.0


def check_presets():
    '''Each preset should have correct mult'''
    es = ESFuturesCommInfo()
    assert es.p.mult == 50.0   # 12.50 / 0.25

    nq = NQFuturesCommInfo()
    assert nq.p.mult == 20.0   # 5.0 / 0.25

    cl = CLFuturesCommInfo()
    assert cl.p.mult == 1000.0  # 10.0 / 0.01

    mes = MESFuturesCommInfo()
    assert mes.p.mult == 5.0    # 1.25 / 0.25

    mnq = MNQFuturesCommInfo()
    assert mnq.p.mult == 2.0    # 0.50 / 0.25


def check_stocklike():
    '''FuturesCommInfo should not be stocklike'''
    comm = FuturesCommInfo(tick_size=0.25, tick_value=12.50, margin=15000)
    assert not comm._stocklike


def test_run(main=False):
    check_mult_derivation()
    check_invalid_tick_size()
    check_pnl()
    check_cash_adjust()
    check_commission()
    check_margin()
    check_presets()
    check_stocklike()

    if main:
        print('All FuturesCommInfo tests passed')


if __name__ == '__main__':
    test_run(main=True)
