# Bug Report: _parse_iso

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/_parse_iso.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when ts is falsy.
  - When ts is a non-empty string, attempts to interpret it as an
    ISO 8601 timestamp.  A trailing "Z" (UTC designator) is accepted
    and treated equivalently to "+00:00".
  - On successful parse, returns a timezone-aware datetime object
    whose components (year, month, day, hour, minute, second,
    microsecond, UTC offset) match the values expressed in ts
    according to ISO 8601 rules.
  - Returns None when ts cannot be parsed as an ISO 8601 timestamp
    (malformed format, invalid date/time values, etc.).

---

### Actual Behavior

If the input 'ts' is falsy (i.e., evaluates to False in a boolean context), the function returns None. Otherwise, 'ts' is a non-empty string. Define t = (ts[:-1] + '+00:00') if ts ends with 'Z' else ts. The function attempts to call datetime.fromisoformat(t). If that call succeeds, the return value is the resulting datetime.datetime object; if any Exception is raised, the return value is None. No non-local state is modified. Formal post-condition: let R be the return value. R = None if (not ts) or (isinstance(ts, str) and datetime.fromisoformat(t) raises an Exception), else R = datetime.fromisoformat(t), where t = (ts[:-1] + '+00:00') if (isinstance(ts, str) and ts.endswith('Z')) else ts. All other program state is unchanged.

---

## Code Evidence

Line 4: if ts.endswith("Z"):
Line 5:     ts = ts[:-1] + "+00:00"
Line 7: return datetime.fromisoformat(ts)

---

## Trigger Condition

The specification requires that on successful parse, the function returns a timezone-aware datetime object. For the input "2023-10-01T12:00:00" (a valid ISO 8601 datetime without an explicit timezone), the code returns a naive datetime (no tzinfo) from datetime.fromisoformat, violating this requirement. The code only makes the datetime aware when a trailing Z is present, but not for other timezone-less timestamps.

---

## How to trigger the bug

The function `_parse_iso` correctly handles the `Z` suffix by rewriting it to `+00:00` before calling `datetime.fromisoformat()`, which makes the result timezone-aware. However, it does not handle the case where a valid ISO 8601 timestamp lacks any timezone designator. For such inputs, `datetime.fromisoformat()` returns a naive datetime (no `tzinfo`), which contradicts the specification requirement that all successful parses return a timezone-aware datetime object.

### Inputs

| Parameter | Value |
|-----------|-------|
| ts | `"2023-10-01T12:00:00"` |

### Expected (spec-correct) Output

A timezone-aware `datetime` object with `tzinfo` not `None`, representing `2023-10-01 12:00:00`.

### Actual (buggy) Output

`datetime.datetime(2023, 10, 1, 12, 0)` — a naive datetime with `tzinfo=None`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, ".")

import dashboard
result = dashboard._parse_iso("2023-10-01T12:00:00")
print(f"result={result!r}, tzinfo={result.tzinfo}")
# actual (buggy) output: result=datetime.datetime(2023, 10, 1, 12, 0), tzinfo=None
# expected (correct) output: tzinfo should not be None (timezone-aware)
```

---

## Probe Script

```python
"""Probe script for dashboard-py--_parse_iso: verify timezone-naive datetime returned for valid ISO 8601 without timezone."""
import sys
import os

# Add repo root to path so `import dashboard` resolves (project is not a package)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard

    ts = "2023-10-01T12:00:00"
    actual = dashboard._parse_iso(ts)

    # Spec requires timezone-aware datetime on successful parse.
    # Bug: actual has no tzinfo (naive datetime) for inputs without explicit timezone.
    passed = actual is not None and actual.tzinfo is None

    if passed:
        print(f"CONFIRMED — _parse_iso({ts!r}) returned naive datetime {actual!r} (tzinfo=None), spec requires timezone-aware")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — _parse_iso('2023-10-01T12:00:00') returned naive datetime datetime.datetime(2023, 10, 1, 12, 0) (tzinfo=None), spec requires timezone-aware
```
