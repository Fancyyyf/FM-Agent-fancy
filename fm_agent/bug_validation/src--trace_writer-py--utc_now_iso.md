# Bug Report: utc_now_iso

**Source file:** `src/trace_writer-py/utc_now_iso.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the current UTC date and time formatted as an ISO 8601 string ending with "Z" as the UTC timezone designator
  - The returned string includes microsecond precision

---

### Actual Behavior

The function returns a string that is the ISO 8601 formatted representation of the current UTC date and time, with the UTC offset suffix '+00:00' replaced by 'Z'. Formally, let t be the instant the function is called, let dt = datetime.now(timezone.utc) at t, then the returned value is dt.isoformat().replace('+00:00', 'Z'). No exceptions are raised, and no side effects occur.

---

## Code Evidence

Line 2: return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

---

## Trigger Condition

The specification requires the returned string to include microsecond precision. However, datetime.isoformat() omits the fractional seconds when microseconds are zero, violating this requirement.

---

## How to trigger the bug

When `datetime.now(timezone.utc)` returns a moment where the microsecond component is exactly zero, `datetime.isoformat()` omits the fractional seconds entirely. The resulting string after `.replace("+00:00", "Z")` will lack the `.000000` microsecond suffix that the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| (none) | `utc_now_iso()` takes no arguments — the bug is probabilistic, manifesting when the system clock microsecond component is zero |

### Expected (spec-correct) Output

`2026-07-17T01:07:29.000000Z`

### Actual (buggy) Output

`2026-07-17T01:07:29Z`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.trace_writer import utc_now_iso

# Call in a loop until microseconds happen to be zero
# (statistically ~1 in 1,000,000 calls)
for _ in range(500_000):
    result = utc_now_iso()
    if '.' not in result:  # no fractional seconds → bug triggered
        print(f"BUG: {result}")  # actual (buggy) output: '2026-07-17T01:07:29Z'
        break
# expected (correct) output: always includes '.ffffff' (e.g. '2026-07-17T01:07:29.000000Z')
```

---

## Probe Script

```python
import os
import re
import sys

# Ensure the repo root is on sys.path so the "src" package is importable.
# The package does not define setuptools entry points; importing via
# its public module path is the correct public entry point.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    from src.trace_writer import utc_now_iso

    # The spec requires ISO 8601 with microsecond precision ending in "Z"
    # Expected format: YYYY-MM-DDTHH:MM:SS.ffffffZ
    iso_with_micros = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$')

    confirmed = False
    failure_value = None
    iterations = 0

    for i in range(500_000):
        result = utc_now_iso()
        iterations = i + 1
        if not iso_with_micros.match(result):
            confirmed = True
            failure_value = result
            break

    if confirmed:
        print(f'CONFIRMED — after {iterations} iterations, output missing microsecond precision: {failure_value!r}')
    else:
        print(f'NOT CONFIRMED — all {iterations} outputs included microsecond precision (YYYY-MM-DDTHH:MM:SS.ffffffZ)')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — after 220303 iterations, output missing microsecond precision: '2026-07-17T01:07:29Z'
```
