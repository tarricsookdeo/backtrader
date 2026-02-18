backtrader
==========

.. image:: https://img.shields.io/badge/python-3.8%2B-blue.svg
   :alt: Python versions
   :scale: 100%

.. image:: https://img.shields.io/badge/license-GPLv3+-green.svg
   :alt: License
   :scale: 100%
   :target: https://github.com/tarricsookdeo/backtrader/blob/master/LICENSE

A fork of the `original backtrader <https://github.com/mementum/backtrader>`_
library, maintained for local development and use. This fork is **not published
to PyPI** — it is installed directly from source.

Quick Start
===========

Prerequisites: `pipenv <https://pipenv.pypa.io/>`_ must be installed
(``pip install pipenv``).

1. **Clone the repository**::

     git clone git@github.com:tarricsookdeo/backtrader.git
     cd backtrader

2. **Install dependencies and the package**::

     pipenv install -e .

   To include plotting support (``matplotlib``)::

     pipenv install matplotlib

3. **Activate the virtual environment**::

     pipenv shell

4. **Verify the installation**::

     python -c "import backtrader as bt; print(bt.__version__)"

You can also run commands without activating the shell by using ``pipenv run``::

  pipenv run python -c "import backtrader as bt; print(bt.__version__)"

Usage
=====

Here is a snippet of a Simple Moving Average CrossOver using a pandas
DataFrame as the data source.
::

  import pandas as pd
  import backtrader as bt

  class SmaCross(bt.SignalStrategy):
      def __init__(self):
          sma1, sma2 = bt.ind.SMA(period=10), bt.ind.SMA(period=30)
          crossover = bt.ind.CrossOver(sma1, sma2)
          self.signal_add(bt.SIGNAL_LONG, crossover)

  # Load your OHLCV data into a pandas DataFrame
  df = pd.read_csv('your_data.csv', index_col='Date', parse_dates=True)

  cerebro = bt.Cerebro()
  cerebro.addstrategy(SmaCross)

  data = bt.feeds.PandasData(dataname=df)
  cerebro.adddata(data)

  cerebro.run()
  cerebro.plot()

There are also many sample scripts in the ``samples/`` directory that
demonstrate various features.

The built-in CLI runner is also available::

  btrun --help

Features
========

Live Trading and backtesting platform written in Python.

  - Data feeds from *pandas* DataFrames (OHLCV)
  - Filters for datas, like breaking a daily bar into chunks to simulate
    intraday or working with Renko bricks
  - Multiple data feeds and multiple strategies supported
  - Multiple timeframes at once
  - Integrated Resampling and Replaying
  - Step by Step backtesting or at once (except in the evaluation of the Strategy)
  - Integrated battery of indicators
  - *TA-Lib* indicator support (needs python *ta-lib* / check the docs)
  - Easy development of custom indicators
  - Analyzers (for example: TimeReturn, Sharpe Ratio, SQN) and ``pyfolio``
    integration (**deprecated**)
  - Flexible definition of commission schemes
  - Integrated broker simulation with *Market*, *Close*, *Limit*, *Stop*,
    *StopLimit*, *StopTrail*, *StopTrailLimit* and *OCO* orders, bracket order,
    slippage, volume filling strategies and continuous cash adjustment for
    future-like instruments
  - Sizers for automated staking
  - Cheat-on-Close and Cheat-on-Open modes
  - Schedulers
  - Trading Calendars
  - Plotting (requires matplotlib)

Requirements
============

  - Python >= ``3.8``
  - ``pandas`` (for data feeds)
  - ``matplotlib`` is optional (for plotting)

Installation
============

This is a **local-only** package. It is not available on PyPI. It uses
`pipenv <https://pipenv.pypa.io/>`_ for dependency and environment management.

**From source**::

  git clone git@github.com:tarricsookdeo/backtrader.git
  cd backtrader
  pipenv install -e .

To include plotting support::

  pipenv install matplotlib


Running Tests
=============

::

  pipenv install pytest --dev
  pipenv run pytest tests/

Documentation
=============

Upstream documentation from the original project:

  - `Blog <http://www.backtrader.com/blog>`_
  - `Documentation <http://www.backtrader.com/docu>`_
  - `Indicators Reference <http://www.backtrader.com/docu/indautoref.html>`_ (122 built-in indicators)
  - `Community <https://community.backtrader.com>`_

See `MODERNIZATION.md <MODERNIZATION.md>`_ for planned improvements in this fork.

Version Numbering
=================

X.Y.Z.I

  - X: Major version number. Should stay stable unless something big is changed
    like an overhaul to use ``numpy``
  - Y: Minor version number. To be changed upon adding a complete new feature or
    (god forbids) an incompatible API change.
  - Z: Revision version number. To be changed for documentation updates, small
    changes, small bug fixes
  - I: Number of Indicators already built into the platform

License
=======

GNU General Public License v3 or later (GPLv3+). See `LICENSE <LICENSE>`_.

This project is a fork of `mementum/backtrader <https://github.com/mementum/backtrader>`_.

Planned: Futures Trading + Prop Firm Rules
==========================================

The following components are planned to extend backtrader for futures trading
with prop firm rule enforcement. Each component is independent and composable.

Component 1: Futures Commission Info [DONE]
---------------------------------------------

Configures futures contract math so P&L, margin, and commissions are
calculated correctly from tick size and tick value.

**Params:**

==============  ===========  =============================================
Param           Default      Description
==============  ===========  =============================================
``tick_size``   ``0.25``     Minimum price increment (e.g. 0.25 for ES)
``tick_value``  ``12.50``    Dollar value per tick per contract
``margin``      ``None``     Margin required per contract in dollars
``commission``  ``0.0``      Fixed commission per contract per side
==============  ===========  =============================================

``mult`` is auto-derived as ``tick_value / tick_size``. Do not set it manually.

**Pre-configured instruments:**

=========================  ==========  ==========  ======  ========  ==========
Class                      tick_size   tick_value   mult    margin    commission
=========================  ==========  ==========  ======  ========  ==========
``ESFuturesCommInfo``      0.25        $12.50      50      $15,000   $2.25
``NQFuturesCommInfo``      0.25        $5.00       20      $20,000   $2.25
``CLFuturesCommInfo``      0.01        $10.00      1000    $5,000    $2.25
``MESFuturesCommInfo``     0.25        $1.25       5       $1,500    $0.50
``MNQFuturesCommInfo``     0.25        $0.50       2       $2,000    $0.50
=========================  ==========  ==========  ======  ========  ==========

**Usage — pre-configured instrument:**
::

  from backtrader.commissions.futures import ESFuturesCommInfo

  cerebro = bt.Cerebro()
  cerebro.broker.addcommissioninfo(ESFuturesCommInfo(), name='ES')

**Usage — custom instrument:**
::

  from backtrader.commissions.futures import FuturesCommInfo

  cerebro.broker.addcommissioninfo(
      FuturesCommInfo(
          tick_size=0.25,
          tick_value=12.50,
          margin=15000.0,
          commission=2.25,
      ),
      name='ES',
  )

**Overriding preset defaults** (e.g. different margin for your broker):
::

  cerebro.broker.addcommissioninfo(
      ESFuturesCommInfo(margin=12000.0, commission=1.50),
      name='ES',
  )

Component 2: Prop Firm Drawdown Analyzer
-----------------------------------------

**New file:** ``backtrader/analyzers/propfirm_drawdown.py``

- ``PropFirmDrawDown(bt.Analyzer)`` with params:

  - ``max_drawdown`` (dollars) — threshold for breach detection
  - ``trailing_mode`` — ``'intraday'`` (HWM updates every bar) or ``'eod'``
    (HWM updates at session end only)
  - ``trail_stop_threshold`` (dollars) — profit level at which trailing stops
    and HWM freezes (common prop firm rule)
  - ``starting_balance`` — auto-detected if not set

- EOD detection: compare bar time to ``data.p.sessionend`` in ``next()``
  (no timer dependency)
- Tracks: HWM, current drawdown, max drawdown, breach events
  (datetime + value + DD amount), whether trailing is frozen
- Breaches are **tracked only** — trading continues
- Accessible from strategy via
  ``self.analyzers.propfirmdrawdown.get_current_drawdown()``
  and ``.is_breached()``

**Modify:** ``backtrader/analyzers/__init__.py`` — add
``from .propfirm_drawdown import *``

Component 3: EOD Position Closer (Strategy Mixin)
---------------------------------------------------

**New file:** ``backtrader/strategies/position_closer.py``

- ``EODPositionCloserMixin`` — strategy mixin using the ``add_timer()`` system
- Params: ``close_time`` (default 15:55), ``cancel_open_orders`` (default True)
- Registers a timer in ``start()``, handles it in ``notify_timer()``
- Cancels open orders then calls ``self.close(data=d)`` for each data with
  a position
- Usage: ``class MyStrat(EODPositionCloserMixin, bt.Strategy):``
- Chains ``super()`` calls so the user's own ``notify_timer`` still works

Component 4: Max Contracts Sizer
----------------------------------

**New file:** ``backtrader/sizers/max_contracts.py``

- ``MaxContractsSizer(bt.Sizer)`` with params:

  - ``max_contracts`` — max position size per instrument
  - ``stake`` — default order size (used if no base_sizer)

- Checks current position, caps order size so total won't exceed limit
- Handles both buy (long cap) and sell (short cap) directions

**Modify:** ``backtrader/sizers/__init__.py`` — add
``from .max_contracts import *``

Component 5: Convenience Setup Helper
---------------------------------------

**New file:** ``backtrader/propfirm.py``

- ``setup_prop_firm(cerebro, ...)`` function that wires up all components
  in one call
- Params: instrument, starting_balance, max_drawdown, trailing_mode,
  trail_stop_threshold, max_contracts
- Sets commission info, cash, adds analyzer, adds sizer
- Note: EOD closing requires the mixin in the strategy class
  (documented in docstring)

Files Summary
--------------

========  =============================================
Action    File
========  =============================================
Create    ``backtrader/commissions/futures.py``
Create    ``backtrader/analyzers/propfirm_drawdown.py``
Create    ``backtrader/strategies/position_closer.py``
Create    ``backtrader/sizers/max_contracts.py``
Create    ``backtrader/propfirm.py``
Modify    ``backtrader/commissions/__init__.py``
Modify    ``backtrader/analyzers/__init__.py``
Modify    ``backtrader/sizers/__init__.py``
========  =============================================
