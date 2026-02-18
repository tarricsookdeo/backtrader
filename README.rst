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

Component 2: Prop Firm Drawdown Analyzer [DONE]
-------------------------------------------------

Tracks trailing drawdown against a configurable limit. Records breach events
but **never stops trading** — purely for analysis and compliance tracking.

**Params:**

==========================  ===============  =============================================
Param                       Default          Description
==========================  ===============  =============================================
``max_drawdown``            ``3000.0``       Dollar drawdown limit before breach is logged
``trailing_mode``           ``'intraday'``   ``'intraday'`` = HWM updates every bar;
                                             ``'eod'`` = HWM updates at session end only
``trail_stop_threshold``    ``None``         Dollar profit at which trailing stops (HWM
                                             freezes at ``starting_balance + threshold``)
``starting_balance``        ``None``         Auto-detected from first bar if not set
``fund``                    ``None``         Auto-detect fundmode from broker
==========================  ===============  =============================================

**How trailing works:**

- The analyzer tracks a high-water mark (HWM) — the highest portfolio value
- Drawdown is measured as ``HWM - current_value``
- In ``intraday`` mode, HWM updates on every bar as value increases
- In ``eod`` mode, HWM only updates when the date changes (session end)
- When ``trail_stop_threshold`` is set and the account reaches
  ``starting_balance + trail_stop_threshold``, the HWM **freezes at the
  threshold level** (not the actual peak). Drawdown becomes static from
  that point forward.

**Example:** Starting balance $50k, trail_stop_threshold $3k, max_drawdown
$2.5k. Account goes to $54k then pulls back to $53k. HWM freezes at $53k
(the threshold). Loss limit is now $53k - $2.5k = $50.5k permanently.

**Analysis output:**

- ``hwm`` — current high-water mark
- ``current_value`` / ``current_drawdown`` — latest values
- ``max_drawdown`` — largest drawdown seen (dollars)
- ``breached`` — True if limit was exceeded
- ``breach_count`` / ``breaches`` — breach event details (datetime, value,
  drawdown, hwm)
- ``trailing_frozen`` / ``frozen_hwm`` — trail freeze state

**Usage:**
::

  from backtrader.analyzers.propfirm_drawdown import PropFirmDrawDown

  cerebro.addanalyzer(
      PropFirmDrawDown,
      max_drawdown=2500.0,
      trailing_mode='eod',
      trail_stop_threshold=3000.0,
      starting_balance=50000.0,
  )

  results = cerebro.run()
  strat = results[0]
  dd = strat.analyzers.propfirmdrawdown.get_analysis()
  print('Max DD: ${}'.format(dd.max_drawdown))
  print('Breached: {}'.format(dd.breached))

  # Convenience methods (also usable during the run from strategy):
  strat.analyzers.propfirmdrawdown.is_breached()
  strat.analyzers.propfirmdrawdown.get_current_drawdown()

Component 3: EOD Position Closer (Strategy Mixin) [DONE]
----------------------------------------------------------

Automatically closes all positions at a configurable time each session.
Uses the backtrader timer system. Cancels open orders then flattens every
position via market order.

**Params** (define on your strategy class):

========================  ========================  ====================================
Param                     Default                   Description
========================  ========================  ====================================
``close_time``            ``datetime.time(15, 55)``  Time to close all positions
``cancel_open_orders``    ``True``                   Cancel pending orders before closing
========================  ========================  ====================================

**Usage:**
::

  import datetime
  from backtrader.strategies.position_closer import EODPositionCloserMixin

  class MyStrategy(EODPositionCloserMixin, bt.Strategy):
      params = (
          ('close_time', datetime.time(15, 55)),
          ('cancel_open_orders', True),
          # ... your strategy params ...
      )

      def __init__(self):
          super(MyStrategy, self).__init__()
          # ... your indicators ...

      def next(self):
          # ... your logic (positions auto-close at close_time) ...
          pass

**Important — MetaParams compatibility:**

Backtrader uses a custom metaclass (``MetaParams``) that merges ``params``
tuples from all base classes. A plain ``object`` mixin cannot define ``params``
as a tuple — the metaclass expects a special ``_derive``-able params object
on base classes, and a raw tuple will cause an ``AttributeError``.

Because of this, ``EODPositionCloserMixin`` does **not** define ``params``
itself. Instead:

1. Define ``close_time`` and ``cancel_open_orders`` as params on **your
   strategy class** (shown in the usage example above).
2. If you omit them, the mixin falls back to built-in defaults
   (``close_time=15:55``, ``cancel_open_orders=True``) via ``getattr``.

**Other notes:**

- The mixin must come **before** ``bt.Strategy`` in the class definition
  so that Python's MRO resolves ``__init__``, ``start``, and
  ``notify_timer`` through the mixin first.
- Always call ``super().__init__()`` in your strategy's ``__init__`` so the
  mixin can register its timer.
- Chains ``super()`` calls so your own ``notify_timer`` still works.

Component 4: Max Contracts Sizer [DONE]
-----------------------------------------

Enforces a maximum open position size per instrument. Caps order size so the
total position (existing + new) never exceeds the limit. Works for both long
and short directions independently.

**Params:**

==================  ===========  =============================================
Param               Default      Description
==================  ===========  =============================================
``max_contracts``   ``10``       Max contracts held at once (long or short)
``stake``           ``1``        Contracts to request per order
==================  ===========  =============================================

**Usage:**
::

  cerebro.addsizer(MaxContractsSizer, max_contracts=3, stake=1)

**How it works:**

- Buying with position at +2 and max_contracts=3: sizer returns 1 (room for 1)
- Buying with position at +3 and max_contracts=3: sizer returns 0 (at limit)
- Selling with position at +3: sizer returns 1 (moving toward flat, always allowed)
- If ``stake`` exceeds remaining room, size is reduced to fit

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
