# Bug Report: _cache_rate

**Source file:** `dashboard-py/_cache_rate.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a 3-tuple (rate, cache_read_sum, input_sum).
  - cache_read_sum is the sum of all cache_read values across rows.
  - input_sum is the sum of all total_input values across rows.
  - When input_sum > 0: rate is cache_read_sum / input_sum, a float
    in the range [0.0, ∞) representing the fraction of total input
    tokens served from cache.
  - When input_sum == 0: rate is 0.0.
  - The type of each sum is determined by the numeric types present
    in rows (the result of adding the values in the sequence).

---

### Actual Behavior

The function returns a tuple (result, cr_total, in_total) such that cr_total = sum(cr for (cr, _) in rows) and in_total = sum(t for (_, t) in rows), both nonnegative. If in_total == 0 then result is None; otherwise result = cr_total / in_total. No exceptions are raised. Formally: ∀ rows where rows is a sequence of pairs (cr, t) with cr ≥ 0 and t ≥ 0, let S_cr = Σ_{(cr, t) ∈ rows} cr and S_t = Σ_{(cr, t) ∈ rows} t. The return value r satisfies: r = (None, S_cr, S_t) if S_t = 0, else r = (S_cr / S_t, S_cr, S_t).

---

## Code Evidence

Line 5: return None, cr_total, in_total

---

## Trigger Condition

When input_sum == 0, the code returns None as the rate, but the specification requires 0.0. For example, with rows = [], cr_total=0, in_total=0, the code returns (None, 0, 0) instead of (0.0, 0, 0).

---

## How to trigger the bug

When `_cache_rate` is called with an empty sequence (no rows), `in_total` evaluates to 0. The code at line 30 (`return None, cr_total, in_total`) returns `None` as the first element of the tuple, but the specification requires `0.0` when `input_sum == 0`.

### Inputs

| Parameter | Value |
|-----------|-------|
| rows | `[]` (empty list) |

### Expected (spec-correct) Output

`(0.0, 0, 0)`

### Actual (buggy) Output

`(None, 0, 0)`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard
result = dashboard._cache_rate([])
assert result == (None, 0, 0)       # actual (buggy) output
# expected (correct) output would be (0.0, 0, 0)
```

---

## Probe Script

```python
import sys
import os

# Ensure we can import the dashboard module from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard
    actual = dashboard._cache_rate([])
    expected = (0.0, 0, 0)
    passed = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: (None, 0, 0) | expected: (0.0, 0, 0)
```
