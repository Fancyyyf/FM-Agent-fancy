# Bug Report: _symbol_range

**Source file:** `src/languages/erlang-py/_symbol_range.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the 'range' sub-dict from symbol when symbol has a 'range' key. Otherwise, returns the 'range' sub-dict from symbol['location'] when symbol has a 'location' key that maps to a truthy dict containing a 'range' key. Returns None when neither path yields a range.

---

### Actual Behavior

The function returns the 'range' value from the LSP symbol response: if the top-level dictionary contains the key 'range', returns symbol['range']; otherwise, if the 'location' key is present and its value is a dictionary containing 'range' (as guaranteed by the precondition), returns symbol['location']['range']; otherwise returns None. The input dictionary is not modified. Formally, let result = _symbol_range(symbol). Then result = (symbol['range'] if 'range' in symbol else (symbol['location']['range'] if 'location' in symbol and 'range' in symbol['location'] else None)).

---

## Code Evidence

Line 4: return (symbol.get("location") or {}).get("range")

---

## Trigger Condition

Code raises AttributeError when symbol['location'] is a truthy non-dict (e.g., a string), but the specification requires returning None because location does not map to a truthy dict containing 'range'.

---

## How to trigger the bug

The bug is triggered when `symbol["location"]` is a truthy value that is not a dictionary (e.g., a string like `"L42C12-L42C24"`). Because `symbol.get("location")` returns the truthy non-dict value, the `or {}` short-circuits and does not fall back to an empty dict. The subsequent `.get("range")` call fails with `AttributeError` because strings (and other non-dict types) have no `.get()` method.

According to the specification, the function should return `None` in this case because `symbol["location"]` does not map to a truthy dict containing a `"range"` key.

### Inputs

| Parameter | Value |
|-----------|-------|
| `symbol` | `{"location": "L42C12-L42C24", "name": "some_func"}` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`AttributeError: 'str' object has no attribute 'get'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _symbol_range

symbol = {"location": "L42C12-L42C24", "name": "some_func"}
result = _symbol_range(symbol)
# actual (buggy) output: AttributeError: 'str' object has no attribute 'get'
# expected (correct) output: None
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Probe must be run from repo root; add repo root to sys.path for imports
sys.path.insert(0, os.getcwd())

# Create a fresh temp directory owned by the probe for any runtime artifacts
probe_workspace = tempfile.mkdtemp(prefix="fm_agent_probe_")

try:
    from src.languages.erlang import _symbol_range

    # Trigger condition: symbol['location'] is a truthy non-dict (e.g., a string)
    # Spec: should return None (location does not map to a truthy dict containing 'range')
    # Bug: (symbol.get("location") or {}).get("range") calls .get() on the string → AttributeError
    symbol = {"location": "L42C12-L42C24", "name": "some_func"}

    try:
        actual = _symbol_range(symbol)
        # No exception → bug not reproduced
        print(f'NOT CONFIRMED — no exception raised; actual: {actual!r} | expected: None')
    except AttributeError as e:
        print(f'CONFIRMED — AttributeError: {e} | expected: None (spec requires returning None)')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    import shutil
    shutil.rmtree(probe_workspace, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — AttributeError: 'str' object has no attribute 'get' | expected: None (spec requires returning None)
```
