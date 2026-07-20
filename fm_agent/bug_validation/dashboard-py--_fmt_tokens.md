# Bug Report: _fmt_tokens

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When n is None, returns "—" (U+2014 em dash).
  - When n is a non-negative numeric value, returns a compact
    human-readable string representation formatted as follows:
      * n ≥ 1,000,000 → value divided by 10⁶, formatted to two
        decimal places, suffixed with "M".
      * 1,000 ≤ n < 1,000,000 → value divided by 10³, formatted
        to one decimal place, suffixed with "K".
      * n < 1,000 → decimal string representation of the integer
        value of n, with no suffix.
  - The returned string is minimal in length for its magnitude
    category; the original value can be approximately recovered by
    multiplying the numeric prefix by the magnitude implied by the
    suffix (10³ for "K", 10⁶ for "M").

---

### Actual Behavior

If n is None, the function returns the string "—". If n is a non-negative number, then: if n >= 1,000,000, returns f"{n/1_000_000:.2f}M"; if 1,000 <= n < 1,000,000, returns f"{n/1_000:.1f}K"; if n < 1,000, returns str(n). Formally, let r be the return value. (n = None → r = "—") ∧ (n ≠ None ∧ n ≥ 1000000 → r = format(n/1000000, ".2f") + "M") ∧ (n ≠ None ∧ 1000 ≤ n < 1000000 → r = format(n/1000, ".1f") + "K") ∧ (n ≠ None ∧ 0 ≤ n < 1000 → r = str(n)).

---

## Code Evidence

Line 79: `return str(n)`

---

## Trigger Condition

The code returns the string representation of the float (e.g., '0.5'), but the specification requires 'decimal string representation of the integer value of n', which would be '0'.

---

## How to trigger the bug

Calling `_fmt_tokens` with a non-integer float value in the range `n < 1,000` triggers the bug. The code applies `str(n)` directly, which preserves the fractional part (e.g., `str(0.5)` → `"0.5"`). The specification requires the decimal representation of the **integer value** of n — i.e., `str(int(n))` — which for `0.5` is `"0"`.

### Inputs

| Parameter | Value |
|-----------|-------|
| n         | `0.5` |

### Expected (spec-correct) Output

`"0"`

### Actual (buggy) Output

`"0.5"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard
# spec requires "decimal string representation of the integer value of n"
# for n < 1,000; integer value of 0.5 is 0
actual = dashboard._fmt_tokens(0.5)
print(repr(actual))  # actual (buggy) output: '0.5'
# expected (correct) output: '0'
```

---

## Probe Script

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard
    # n < 1,000 with a float value: spec requires "decimal string representation
    # of the integer value of n", which for 0.5 is "0". Code does str(n) = "0.5".
    actual   = dashboard._fmt_tokens(0.5)
    expected = "0"
    passed   = actual != expected
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
CONFIRMED — actual: '0.5' | expected: '0'
```
