# Bug Report: State::elapsed

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns None if no events have been ingested into the state. Otherwise returns a non-negative float representing the elapsed duration in seconds from the earliest recorded event's start time to the latest recorded event's end time, or to the current UTC timestamp if no end time has been recorded.

---

### Actual Behavior

After execution, the instance `self` remains unchanged. If `self.first_event_time` is `None`, the method returns `None` (). Otherwise, it returns the elapsed seconds as a float computed by subtracting `self.first_event_time` from the effective end time, which is `self.last_event_time` if it is not `None`, else the current UTC time obtained from `datetime.now(timezone.utc)`. Formally: 
Return value R satisfies: 
(R = None  self.first_event_time = None)  
(R  None  let end = (self.last_event_time if self.last_event_time  None else datetime.now(timezone.utc)) in R = (end - self.first_event_time).total_seconds()).
No exceptions are raised, and no side effects occur.

---

## Code Evidence

Line 4: end = self.last_event_time or datetime.now(timezone.utc)
Line 5: return (end - self.first_event_time).total_seconds()

---

## Trigger Condition

When last_event_time is earlier than first_event_time, the code computes a negative elapsed seconds, violating the specification's requirement to return a non-negative float.

---

## How to trigger the bug

The `elapsed()` method computes `(end - self.first_event_time).total_seconds()` without any safeguard against negative results. When `last_event_time` is earlier than `first_event_time` — which can occur via direct attribute assignment, serialization/deserialization, or concurrency — the subtraction yields a negative float. The specification explicitly requires a "non-negative float".

### Inputs

| Parameter | Value |
|-----------|-------|
| `self.first_event_time` | `datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)` (future) |
| `self.last_event_time` | `datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)` (past, earlier than first) |

### Expected (spec-correct) Output

A non-negative float (e.g., `0.0` or the absolute difference `172800.0`).

### Actual (buggy) Output

`-172800.0` (negative float — 48 hours, but with the wrong sign)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import State
from datetime import datetime, timezone

state = State("/tmp")

# Set first_event_time to a LATER time than last_event_time
state.first_event_time = datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)
state.last_event_time  = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)

print(state.elapsed())
# actual (buggy) output: -172800.0
# expected (correct) output: a non-negative float (e.g., 0.0 or 172800.0)
```

---

## Probe Script

```python
import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta

# Add repo root to sys.path so 'import dashboard' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from dashboard import State

    # Create probe workspace under a fresh temp directory (self-validation guard)
    probe_tmp = tempfile.mkdtemp(prefix="probe_elapsed_")

    # Instantiate State — uses the temp dir which has no trace/ subdir,
    # so _locate_workdir returns <tempdir>/fm_agent (no write occurs)
    state = State(probe_tmp)

    # Trigger condition: last_event_time earlier than first_event_time
    future_time = datetime(2026, 7, 30, 12, 0, 0, tzinfo=timezone.utc)
    past_time   = datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc)

    state.first_event_time = future_time
    state.last_event_time  = past_time

    actual   = state.elapsed()
    # Specification requires non-negative float; negative result = bug confirmed
    expected = abs(future_time - past_time).total_seconds()  # what should be reported
    passed   = actual < 0  # True → bug reproduced (negative elapsed returned)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Clean up temp directory
    try:
        os.rmdir(probe_tmp)
    except Exception:
        pass

if passed:
    print(f'CONFIRMED — actual: {actual!r} (negative) | expected: {expected!r} (non-negative) | '
          f'bug: elapsed() returns negative when last_event_time < first_event_time')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: -172800.0 (negative) | expected: 172800.0 (non-negative) | bug: elapsed() returns negative when last_event_time < first_event_time
```
