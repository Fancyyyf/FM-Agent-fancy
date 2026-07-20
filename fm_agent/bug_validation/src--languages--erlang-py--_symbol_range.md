# Bug Report: _symbol_range

**Source file:** `src/languages/erlang-py/_symbol_range.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the "range" value associated with the symbol, or None when no range
    can be located
  - When symbol contains a "range" key, returns its value
  - When symbol lacks a "range" key but contains a truthy "location" key, returns
    the "range" value from that location
  - When symbol lacks both a "range" key and a truthy "location" key containing a
    "range", returns None
  - The returned value is the raw range dict without transformation

---

### Actual Behavior

The function returns the range of the LSP symbol without modifying `symbol`. If `"range"` is a key in `symbol`, its value is returned. Otherwise, if `symbol` has a key `"location"` whose value is truthy (e.g., a dict), the value of the `"range"` key inside that sub-dict is returned; if `"location"` is missing or falsy, `None` is returned. No exceptions are raised. Formally: post-condition  (unchanged(symbol)  return = (symbol['range'] if 'range'  symbol else (symbol.get('location') or {}).get('range')))

---

## Code Evidence

```python
Line 4: return (symbol.get("location") or {}).get("range")
```

In the actual source file (`src/languages/erlang.py`, line 470):
```python
return (symbol.get("location") or {}).get("range")
```

---

## Trigger Condition

If 'location' is truthy but lacks a 'get' method (e.g., a string), the code raises an AttributeError instead of returning None as required by the specification.

---

## How to trigger the bug

When `_symbol_range` receives a `symbol` dict where the `"location"` key has a truthy value that is not a dict (e.g., a string like `"some/path.erl"`), the expression `(symbol.get("location") or {}).get("range")` short-circuits to the truthy value (the string) and then calls `.get("range")` on it. Since strings do not have a `.get()` method, an `AttributeError` is raised instead of returning `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| symbol | `{"location": "some/path.erl"}` |

### Expected (spec-correct) Output

`None` (no range can be located because the location value is not a dict with a "range" key)

### Actual (buggy) Output

`AttributeError: 'str' object has no attribute 'get'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _symbol_range

# location is a truthy string instead of a dict
symbol = {"location": "some/path.erl"}
result = _symbol_range(symbol)
# actual (buggy) output: AttributeError: 'str' object has no attribute 'get'
# expected (correct) output: None
```

---

## Probe Script

```python
import sys
import os

# Add workspace root to path so `src` is importable
_workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _workspace not in sys.path:
    sys.path.insert(0, _workspace)

try:
    from src.languages.erlang import _symbol_range

    # Trigger condition: 'location' is truthy but not a dict (e.g., a string)
    # Expected (spec-correct): returns None
    # Actual (buggy): raises AttributeError because string has no .get() method
    symbol = {"location": "some/path.erl"}

    try:
        actual = _symbol_range(symbol)
        # If we reach here, no exception was raised
        expected = None  # spec says should return None when location has no 'range'
        passed = actual != expected
        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    except AttributeError as e:
        # Bug reproduced: spec says return None, but we got AttributeError
        print(f"CONFIRMED — AttributeError raised: {e} | expected: None (no range found)")
    except Exception as e:
        print(f"ERROR: unexpected exception type {type(e).__name__}: {e}")
        sys.exit(1)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — AttributeError raised: 'str' object has no attribute 'get' | expected: None (no range found)
```
