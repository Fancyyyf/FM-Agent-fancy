# Bug Report: elapsed

**Source file:** `dashboard.py#State.elapsed`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when self.first_event_time is None (no events have
    been recorded yet)
  - Otherwise returns the elapsed wall-clock duration between
    self.first_event_time and the endpoint timestamp, expressed as a
    possibly-fractional number of seconds
  - The endpoint timestamp is self.last_event_time when
    self.last_event_time is truthy; when self.last_event_time is
    falsy (None or absent), the current UTC wall-clock instant is
    used as the endpoint instead

---

### Actual Behavior

If `self.first_event_time` is None, the method returns None with no side effects. Otherwise, let `end` be `self.last_event_time` if it is not None, else the result of `datetime.now(timezone.utc)` evaluated at the time of the call. Then the method returns `(end - self.first_event_time).total_seconds()`, a float representing the duration in seconds between `self.first_event_time` and `end`. No side effects on the object state.

---

## Code Evidence

Line 4: end = self.last_event_time or datetime.now(timezone.utc)

---

## Trigger Condition

The specification explicitly states that when self.last_event_time is falsy (None or absent), the current UTC wall-clock instant should be used. The code accesses self.last_event_time directly without guarding against its absence, causing an AttributeError when the attribute does not exist. This violates the specification, which expects the method to handle the absent case gracefully by using the current time.

---

## How to trigger the bug

The `State.elapsed()` method at line 508 of `dashboard.py` accesses `self.last_event_time` via `self.last_event_time or datetime.now(timezone.utc)`. This handles the `None` case correctly (falsy → falls through to `datetime.now`), but raises `AttributeError` when the attribute does not exist at all. The `__init__` method always sets `self.last_event_time = None`, so under normal construction the attribute is always present. However, the specification explicitly promises that the "absent" case is handled, and the code does not fulfill this promise — it crashes instead of falling back to the current UTC time.

### Inputs

| Parameter | Value |
|---|---|
| `state.first_event_time` | `datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)` |
| `state.last_event_time` | *absent* (attribute deleted via `del state.last_event_time`) |

### Expected (spec-correct) Output

A float representing the elapsed wall-clock seconds between `datetime(2026, 1, 1, ...)` and the current UTC time.

### Actual (buggy) Output

`AttributeError: 'State' object has no attribute 'last_event_time'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import State
from datetime import datetime, timezone

state = State('.')
state.first_event_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
del state.last_event_time   # simulate absent attribute
state.elapsed()              # raises AttributeError
# actual (buggy) output: AttributeError: 'State' object has no attribute 'last_event_time'
# expected (correct) output: float (elapsed seconds from Jan 1 2026 to now)
```

---

## Probe Script

```python
import os
import sys

# Ensure the repo root is on sys.path so that `dashboard` is importable
# when the script is run from the repo root.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from datetime import datetime, timezone

try:
    from dashboard import State
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

def main():
    try:
        # Create a minimal State instance. _locate_workdir() falls back to
        # project_root / "fm_agent" which exists under the snapshot.
        state = State(_repo_root)

        # Set first_event_time to a non-None value so elapsed() does not
        # return early at the None guard.
        state.first_event_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        # Simulate the "absent" case described in the trigger condition:
        # delete the last_event_time attribute entirely.
        del state.last_event_time

        # Call elapsed(). If the bug exists, this raises AttributeError
        # because line 508 accesses self.last_event_time directly.
        result = state.elapsed()
        print(f'NOT CONFIRMED — elapsed() returned {result!r} despite absent last_event_time')

    except AttributeError as e:
        # Bug confirmed: code crashes when last_event_time attribute is absent,
        # violating the spec which says the method should handle "absent" gracefully.
        print(f'CONFIRMED — AttributeError when last_event_time is absent: {e}')
    except Exception as e:
        print(f'ERROR: unexpected {type(e).__name__}: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### Probe Output

```
CONFIRMED — AttributeError when last_event_time is absent: 'State' object has no attribute 'last_event_time'
```
