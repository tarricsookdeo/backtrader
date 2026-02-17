# Backtrader Modernization Opportunities

## Overview
This is a fork of [mementum/backtrader](https://github.com/mementum/backtrader), maintained at [tarricsookdeo/backtrader](https://github.com/tarricsookdeo/backtrader). The original project is no longer actively maintained. This fork targets Python 3.8+ and is installed locally from source (not available on PyPI).

This document outlines modernization opportunities using Python 3.8+ features.

## Current State
- **Files**: 171 Python files
- **Lines of Code**: ~50,000+
- **Python Compatibility**: 3.8+ (Python 2 support removed)
- **Architecture**: Synchronous, event-driven backtesting engine
- **Installation**: Local only via `pip install -e .` (no PyPI package)

---

## 1. High-Impact Modernizations

### 1.1 Native Metaclass Syntax (Python 3)
**Current:**
```python
class Cerebro(with_metaclass(MetaParams, object)):
```

**Modern:**
```python
class Cerebro(metaclass=MetaParams):
```

**Impact**: 89 occurrences across codebase
**Benefits**: 
- Cleaner syntax
- Better IDE support
- Removes dependency on `with_metaclass` helper

---

### 1.2 F-Strings for String Formatting (Python 3.6+)
**Current:**
```python
'Order {}: {} @ {}'.format(order.ref, price, size)
```

**Modern:**
```python
f'Order {order.ref}: {price} @ {size}'
```

**Impact**: ~200+ string formatting operations
**Benefits**:
- 10-20% faster string formatting
- Better readability
- Compile-time syntax checking

---

### 1.3 Type Hints (Python 3.5+)
**Current:**
```python
def __init__(self, params, **kwargs):
    self.p = self.params = params
```

**Modern:**
```python
from typing import Any, Optional

def __init__(self, params: dict[str, Any], **kwargs: Any) -> None:
    self.p = self.params = params
```

**Impact**: Entire codebase
**Benefits**:
- Better IDE autocomplete
- Static type checking with mypy
- Self-documenting code
- Catch bugs at development time

---

### 1.4 Dataclasses (Python 3.7+)
**Current:**
```python
class OptReturn(object):
    def __init__(self, params, **kwargs):
        self.p = self.params = params
        for k, v in kwargs.items():
            setattr(self, k, v)
```

**Modern:**
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class OptReturn:
    params: dict[str, Any]
    
    def __post_init__(self):
        self.p = self.params
```

**Impact**: Simple data container classes
**Benefits**:
- Auto-generated __init__, __repr__, __eq__
- Less boilerplate
- Immutable option with frozen=True

---

### 1.5 Walrus Operator := (Python 3.8+)
**Current:**
```python
result = some_calculation()
if result:
    use_result(result)
```

**Modern:**
```python
if result := some_calculation():
    use_result(result)
```

**Benefits**:
- Reduces variable scope
- Cleaner code in loops and conditions

---

## 2. Async/Await Support (Major Feature)

### Current Architecture
Backtrader is **fully synchronous**. Data feeds, broker connections, and strategy execution all run in a single thread with event loops.

### Async Opportunities

#### 2.1 Async Data Feeds
**Current:**
```python
def _load(self):
    # Blocking network call
    data = requests.get(url)
    return True
```

**Modern:**
```python
import asyncio
import aiohttp

async def _load(self):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
    return True
```

**Benefits**:
- Fetch multiple data sources concurrently
- Better CPU utilization during I/O waits
- Support for WebSocket real-time feeds

#### 2.2 Async Broker Integration
**Current:**
```python
def buy(self, ...):
    order = self.broker.place_order(...)
    # Blocks until response
    return order
```

**Modern:**
```python
async def buy(self, ...):
    order = await self.broker.place_order(...)
    # Other strategies can run while waiting
    return order
```

**Benefits**:
- Handle multiple concurrent orders
- Better integration with async broker APIs
- Live trading without blocking

#### 2.3 Async Backtesting Engine
```python
async def run(self):
    tasks = []
    for data in self.datas:
        tasks.append(asyncio.create_task(data.load()))
    
    while any(not d.islive() for d in self.datas):
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # Process completed data, run strategies
```

**Challenges**:
- Breaking API change
- Requires rewriting core engine
- Compatibility with existing strategies

**Implementation Path**:
```python
# Option 1: Parallel async (new method)
cerebro.run_async()  # New async method

# Option 2: Hybrid approach
cerebro.opt_async()  # Async optimization only
```

---

## 3. Performance Improvements

### 3.1 Vectorized Operations with NumPy (Existing but enhanced)
Backtrader already uses numpy, but could leverage:
- **Numba**: JIT compilation for indicator calculations
- **Pandas 2.0**: PyArrow backend for better performance

### 3.2 Multiprocessing with concurrent.futures (Python 3.2+)
**Current:**
```python
import multiprocessing
pool = multiprocessing.Pool()
```

**Modern:**
```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=maxcpus) as executor:
    results = executor.map(optimize_strategy, param_combinations)
```

**Benefits**:
- Better API
- Easier error handling
- Future-based results

### 3.3 Generators with yield from (Python 3.3+)
**Current:**
```python
def __iter__(self):
    for line in self.lines:
        yield line
```

**Modern:**
```python
def __iter__(self):
    yield from self.lines
```

---

## 4. Code Quality Improvements

### 4.1 Remove Python 2 Compatibility Code
**Files to clean up:**
- `backtrader/utils/py3.py` - Entire file can be removed
- All `from __future__ import ...` statements
- `object` inheritance in classes
- `long`, `unicode`, `xrange` compatibility shims

**Impact**: ~500 lines of compatibility code removed

### 4.2 Context Managers with contextlib (Python 3.2+)
```python
from contextlib import contextmanager

@contextmanager
def data_source(url):
    conn = create_connection(url)
    try:
        yield conn
    finally:
        conn.close()
```

### 4.3 Better Exception Handling (Python 3.11+)
```python
# Exception groups for parallel processing
try:
    async with asyncio.TaskGroup() as tg:
        for data in datas:
            tg.create_task(data.load())
except* ConnectionError as eg:
    for err in eg.exceptions:
        logger.error(f"Connection failed: {err}")
```

---

## 5. Architecture Modernizations

### 5.1 Event System with dataclasses
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass(frozen=True)
class MarketEvent:
    timestamp: datetime
    symbol: str
    event_type: Literal['tick', 'bar', 'order']
    data: dict
```

### 5.2 Protocol Classes for Interfaces (Python 3.8+)
```python
from typing import Protocol

class DataFeed(Protocol):
    def load(self) -> bool: ...
    def islive(self) -> bool: ...
    def close(self) -> None: ...
```

### 5.3 Dependency Injection with modern patterns
```python
from typing import Callable

class Cerebro:
    def __init__(
        self,
        preload: bool = True,
        broker_factory: Callable[[], Broker] = BackBroker,
    ):
        self.broker = broker_factory()
```

---

## 6. Specific File Modernizations

### 6.1 `cerebro.py` (1,700+ lines)
- Split into smaller modules
- Add async run method
- Type hints for all public methods
- Use dataclasses for OptReturn

### 6.2 `lineiterator.py` and `linebuffer.py`
- Native metaclass syntax
- F-strings in string representations
- Type hints for line operations

### 6.3 `stores/` (IB, Oanda, VC)
- Async versions of store interfaces
- Context managers for connections
- Better error handling with exception groups

### 6.4 `brokers/`
- Protocol-based broker interface
- Async order placement
- Type-safe order parameters

---

## 7. Implementation Priority

### Phase 1: Cleanup (Low Risk)
1. Remove `from __future__` imports
2. Remove `with_metaclass` -> native syntax
3. F-string conversion
4. Add type hints to public APIs

### Phase 2: Performance (Medium Risk)
1. concurrent.futures for optimization
2. Better multiprocessing
3. Numba for indicators (optional)

### Phase 3: Async (High Risk, High Reward)
1. Async data feeds
2. Async broker API
3. Hybrid sync/async cerebro

---

## 8. Migration Strategy

### Backward Compatibility
- Maintain sync API as default
- Add `_async` suffix for async methods
- Deprecation warnings for removed features

### Testing
- Full test suite must pass
- Benchmark before/after performance
- Test async paths separately

---

## Summary Table

| Feature | Python Version | Effort | Impact | Priority |
|---------|---------------|--------|--------|----------|
| Remove Python 2 code | 3.8+ | Low | Medium | High |
| F-strings | 3.6+ | Low | Low | Medium |
| Native metaclasses | 3.0+ | Medium | Medium | High |
| Type hints | 3.5+ | High | High | Medium |
| Dataclasses | 3.7+ | Medium | Medium | Low |
| concurrent.futures | 3.2+ | Medium | Medium | Medium |
| Async/await | 3.5+ | Very High | Very High | Low |
| Exception groups | 3.11+ | Low | Low | Low |

---

## Recommendation

**Start with Phase 1 (cleanup)** - it's low risk and improves maintainability. The async features (Phase 3) would be the most impactful for modern use cases but require significant architectural changes.
