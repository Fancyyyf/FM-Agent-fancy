# Bug Report: _cache_rate

**Source file:** `fm_agent/extracted_functions/dashboard-py/_cache_rate.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a tuple (rate, cr_sum, in_sum) where cr_sum is the sum of all cache_read_count values across rows, in_sum is the sum of all total_count values across rows, and rate is cr_sum / in_sum when in_sum > 0, or 0.0 when in_sum equals 0. rate is in the closed interval [0.0, 1.0]. Both cr_sum and in_sum are non-negative integers. The original rows argument is not mutated.

---

### Actual Behavior

After the function executes, it returns a triple (ratio, cr_sum, in_sum) where cr_sum is the sum of all first elements (cache_read_count) of the tuples in rows, and in_sum is the sum of all second elements (total_count). If in_sum is 0, ratio is None; otherwise ratio is cr_sum divided by in_sum (as a float). No exceptions are raised and no external state is modified. Formally, given rows = [(c_i, t_i)] with 0  c_i  t_i, define CR =  c_i and IN =  t_i. The return value r satisfies r[1] = CR, r[2] = IN, and (IN == 0  r[0] = None)  (IN > 0  r[0] = CR / IN).

---

## Code Evidence

Line 5: return None, cr_total, in_total

---

## Trigger Condition

When in_total is 0, the specification requires rate=0.0, but the code returns None for rate.

---

## How to trigger the bug

Call `_cache_rate` with an input where total_count sums to 0. The simplest case is an empty list `[]`, which yields `cr_total=0, in_total=0`. The code returns `(None, 0, 0)`, but the specification requires `(0.0, 0, 0)`.

### Inputs

| Parameter | Value |
|-----------|-------|
| rows | `[]` (empty list) |

### Expected (spec-correct) Output

`(0.0, 0, 0)`

### Actual (buggy) Output

`(None, 0, 0)`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard
result = dashboard._cache_rate([])
assert result == (0.0, 0, 0), f"Expected (0.0, 0, 0), got {result!r}"
# actual (buggy) output: (None, 0, 0)
# expected (correct) output: (0.0, 0, 0)
```

---

## Probe Script

```python
"""Probe script for bug dashboard-py--_cache_rate.

Bug: _cache_rate returns None for rate when in_total is 0, but the specification
requires rate=0.0 in that case.

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
    _cache_rate = dashboard._cache_rate

    # Trigger: empty rows → cr_total=0, in_total=0 → bug path
    actual = _cache_rate([])

    # Spec: rate=0.0 when in_sum=0; cr_sum=0, in_sum=0
    expected = (0.0, 0, 0)

    # Bug reproduced if actual[0] is None instead of 0.0
    passed = actual[0] is not expected[0]

    if passed:
        print(
            f"CONFIRMED — _cache_rate returned rate={actual[0]!r} "
            f"instead of expected rate={expected[0]!r} when in_total=0. "
            f"Full return: actual={actual!r} | expected={expected!r}"
        )
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
CONFIRMED — _cache_rate returned rate=None instead of expected rate=0.0 when in_total=0. Full return: actual=(None, 0, 0) | expected=(0.0, 0, 0)
```
