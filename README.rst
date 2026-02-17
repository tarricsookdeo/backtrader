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

Here is a snippet of a Simple Moving Average CrossOver. It can be done in
several different ways. Use the docs (and examples) Luke!
::

  from datetime import datetime
  import backtrader as bt

  class SmaCross(bt.SignalStrategy):
      def __init__(self):
          sma1, sma2 = bt.ind.SMA(period=10), bt.ind.SMA(period=30)
          crossover = bt.ind.CrossOver(sma1, sma2)
          self.signal_add(bt.SIGNAL_LONG, crossover)

  cerebro = bt.Cerebro()
  cerebro.addstrategy(SmaCross)

  data0 = bt.feeds.YahooFinanceData(dataname='MSFT', fromdate=datetime(2011, 1, 1),
                                    todate=datetime(2012, 12, 31))
  cerebro.adddata(data0)

  cerebro.run()
  cerebro.plot()

There are also many sample scripts in the ``samples/`` directory that
demonstrate various features.

The built-in CLI runner is also available::

  btrun --help

Features
========

Live Trading and backtesting platform written in Python.

  - Live Data Feed and Trading with

    - Interactive Brokers (needs ``IbPy`` and benefits greatly from an
      installed ``pytz``)
    - *Visual Chart* (needs a fork of ``comtypes`` until a pull request is
      integrated in the release and benefits from ``pytz``)
    - *Oanda* (needs ``oandapy``) (REST API Only - v20 did not support
      streaming when implemented)

  - Data feeds from csv/files, online sources or from *pandas* and *blaze*
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
  - No external dependencies for core functionality
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

For *IB* Data Feeds/Trading:

  - ``IbPy`` doesn't seem to be in PyPi. Do either::

      pipenv install git+https://github.com/blampe/IbPy.git#egg=IbPy

    or (if ``git`` is not available in your system)::

      pipenv install https://github.com/blampe/IbPy/archive/master.zip

For other functionalities like: ``Visual Chart``, ``Oanda``, ``TA-Lib``, check
the dependencies in the upstream documentation.

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
