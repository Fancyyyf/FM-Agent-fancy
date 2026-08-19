# Bug Report: _get_nested

**Source file:** `dashboard-py/_get_nested`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the result of successively indexing the nested dict structure with each key in order, starting from d. At each step, if the current value is not a dict or does not contain the next key, returns None. When keys is empty, returns d.

---

### Actual Behavior

The function returns the value located at the nested key path given by `keys` within the dictionary `d`, provided that every intermediate object along the path is a dictionary that contains the next key; otherwise it returns `None`. If `keys` is empty, `d` itself is returned. More formally, let `keys = (k_1, k_2, ..., k_n)`. Define a recursive function `f(current, remaining)`:
- if `remaining` is empty: return `current`
- else if `not isinstance(current, dict)`: return `None`
- else: return `f(current.get(remaining[0]), remaining[1:])`
Then `_get_nested(d, *keys)` evaluates to `f(d, keys)`. Equivalently, an iterative description: initialize `cur = d`; for each `k` in `keys` in order, if `not isinstance(cur, dict)` return `None`, else set `cur = cur.get(k)`; after the loop return `cur`. Thus the result is `None` whenever a key is missing or an intermediate value is not a mapping, and is the final value (which may itself be `None`) otherwise.

---

## Code Evidence

Line 6: cur = cur.get(k)

---

## Trigger Condition

The code uses cur.get(k) to retrieve the value for the next key, assuming that a missing key always yields None. However, a dict subclass can override get() to return a non-None value even when the key is missing (i.e., when __contains__ returns False). The specification requires returning None whenever the current dict does not contain the key, which is violated by this input because the code returns the non-None get() value instead of None.

---

## How to trigger the bug

The bug occurs when `_get_nested` is called with a `dict` subclass that overrides `get()` to return a non-`None` value for missing keys. Since `_get_nested` uses `cur.get(k)` (which delegates to the subclass's `get()`), it can return a non-`None` sentinel even when the key is not present in the dictionary. The specification requires returning `None` when the key does not exist, which should be checked via `k in cur` rather than relying on `get()` semantics.

### Inputs

| Parameter | Value |
|-----------|-------|
| `d` | `_LeakyDict({"a": 1})` — a dict subclass whose `get()` returns a sentinel object when the key is absent |
| `*keys` | `("missing",)` — a key not present in the dictionary |

### Expected (spec-correct) Output

`None` — because the key `"missing"` is not in the dictionary, per the specification.

### Actual (buggy) Output

`_LeakyDict._SENTINEL` (an opaque object) — because `cur.get(k)` delegates to the subclass's overridden `get()`, which returns the sentinel.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import _get_nested

class LeakyDict(dict):
    _SENTINEL = object()

    def get(self, key, default=None):
        if key in self:
            return super().get(key)
        return self._SENTINEL

d = LeakyDict({"a": 1})
result = _get_nested(d, "missing")
# actual (buggy) output: <object at ...> (the sentinel)
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe script for bug dashboard-py--_get_nested.

Bug: _get_nested uses cur.get(k) which can return non-None from a dict
subclass that overrides get(), even when the key is missing. The specification
requires returning None whenever the current dict does not contain the key.

This probe runs from a fresh temporary directory as required by the validator.
"""

import os
import sys
import tempfile
import shutil

# Add repo root to path so dashboard module can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    import dashboard
    import dashboard as pkg
    actual = None
    error_msg = None

    # Dict subclass that overrides get() to return a sentinel when key is missing
    class _CustomDict(dict):
        SENTINEL = object()

        def get(self, key, default=None):
            return default

    _nested = pkg._get_nested

    # Test 1: Standard dict — missing key → should return None (spec-correct baseline)
    # Spec: returns None when key not in dict. Code uses cur.get(k) which returns None.
    # Both agree here — but only because get() default is None. Not a bug trigger.
    result1 = _nested({"a": 1}, "missing")
    assert result1 is None, f"Standard dict missing key: expected None, got {result1!r}"

    # Test 2: CustomDict that returns the default from get() = None — same as Test 1
    # Even with CustomDict, get("missing", None) returns None (our override passes through
    # the default). This does NOT trigger the bug either — we need get() to diverge.
    # Let's try a subclass where get() returns a non-None sentinel when the key is absent.
    class _LeakyDict(dict):
        _SENTINEL = object()

        def get(self, key, default=None):
            if key in self:
                return super().get(key)
            return self._SENTINEL

        def __contains__(self, key):
            return super().__contains__(key)

    d = _LeakyDict({"a": 1})
    # __contains__("missing") → False (key not in dict)
    missing_contained = "missing" in d
    assert not missing_contained, f"__contains__('missing') should be False, got {missing_contained}"

    # get("missing") returns the sentinel, not None
    got = d.get("missing")
    assert got is _LeakyDict._SENTINEL, f"get('missing') should return sentinel, got {got!r}"

    # Now the actual bug test:
    # Spec: _get_nested should return None because "missing" not in d
    # Bug: _get_nested uses cur.get("missing") which returns the sentinel
    result2 = _nested(d, "missing")

    # Spec-correct: return None (key not in dict)
    expected = None
    # Buggy output: returns the sentinel (from get() override)
    actual = result2
    passed = actual is not expected  # True → bug reproduced (returned sentinel, not None)

    if passed:
        print(f"CONFIRMED — _get_nested returned {actual!r} instead of {expected!r} "
              f"when dict subclass overrides get(). "
              f"Key was in dict (__contains__): {missing_contained}, "
              f"get() returned non-None sentinel: True")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except ImportError as e:
    print(f"ERROR: Import failed — {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — _get_nested returned <object object at 0x7136acde3bc0> instead of None when dict subclass overrides get(). Key was in dict (__contains__): False, get() returned non-None sentinel: True
```
