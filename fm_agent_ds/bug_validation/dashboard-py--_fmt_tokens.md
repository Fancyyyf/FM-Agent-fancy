# Bug Report: _fmt_tokens

**Source file:** `fm_agent/extracted_functions/dashboard-py/_fmt_tokens.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a human-readable string representation of n. When n >= 1,000,000, the value is formatted with at most one decimal place followed by the suffix 'M'. When n >= 1,000 and n < 1,000,000, the value is formatted with at most one decimal place followed by the suffix 'K'. When n < 1,000, the value is formatted as a plain integer string with no suffix. The returned string contains no Rich markup, no leading or trailing whitespace, and is suitable for inline display. The string consists solely of ASCII digits, an optional single '.' character, an optional suffix letter ('K' or 'M'), and no other characters.

---

### Actual Behavior

The function returns a string representing n: if n >= 1,000,000, it returns the string f"{n/1_000_000:.2f}M"; if 1,000 <= n < 1,000,000, it returns f"{n/1_000:.1f}K"; otherwise (0 <= n < 1,000) it returns str(n). Formally, let result be the return value. Then: (n >= 1000000 => result = f"{n/1000000:.2f}M") AND (1000 <= n < 1000000 => result = f"{n/1000:.1f}K") AND (0 <= n < 1000 => result = str(n)).

---

## Code Evidence

Line 5: return f"{n/1_000_000:.2f}M"

---

## Trigger Condition

Code returns '1.00M' with two decimal places, but specification requires at most one decimal place for values >= 1,000,000.

---

## How to trigger the bug

The function uses `:.2f` format specifier for M-range values (n >= 1,000,000), which always produces exactly two decimal places. However, the specification requires "at most one decimal place". Calling `_fmt_tokens(1_000_000)` produces `"1.00M"` with two decimal places, violating the spec.

### Inputs

| Parameter | Value |
|-----------|-------|
| n | 1_000_000 |

### Expected (spec-correct) Output

`"1.0M"` (at most one decimal place)

### Actual (buggy) Output

`"1.00M"` (two decimal places — `:.2f` format)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import dashboard
result = dashboard._fmt_tokens(1_000_000)
# actual (buggy) output: '1.00M'
# expected (correct) output: '1.0M'
```

---

## Probe Script

```py
"""Probe script for bug dashboard-py--_fmt_tokens.

Bug: _fmt_tokens formats M-range values with two decimal places (:.2f),
but the specification requires at most one decimal place.
"""

import os
import sys

# Add repo root to path so dashboard module can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    import dashboard
    actual = dashboard._fmt_tokens(1_000_000)

    # Spec says "at most one decimal place" for M values.
    # The code uses .2f → always 2 decimal places → bug.
    if actual.endswith("M"):
        body = actual[:-1]
        decimal_places = len(body.split(".")[1]) if "." in body else 0
        passed = decimal_places > 1
    else:
        decimal_places = 0
        passed = False

    if passed:
        expected_example = f"{1_000_000/1_000_000:.1f}M"
        print(
            f"CONFIRMED — _fmt_tokens(1_000_000) returned {actual!r} "
            f"({decimal_places} decimal places), "
            f"but spec allows at most 1 decimal place (e.g. {expected_example!r})"
        )
    else:
        print(f"NOT CONFIRMED — actual: {actual!r}")

except ImportError as e:
    print(f"ERROR: Import failed — {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — _fmt_tokens(1_000_000) returned '1.00M' (2 decimal places), but spec allows at most 1 decimal place (e.g. '1.0M')
```
