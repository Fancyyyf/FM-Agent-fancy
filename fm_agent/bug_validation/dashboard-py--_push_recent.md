# Bug Report: State._push_recent

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/_push_recent.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- A 4-tuple (when_str, stage, status, summary) is present at the most
    recently added position of self.recent_events, where when_str is the
    "HH:MM:SS"-formatted string of ts if ts is not None, or "" (empty
    string) if ts is None.
  - If self.recent_events was at maximum capacity before the call, the
    chronologically oldest entry is evicted.
  - Every other entry in self.recent_events retains its relative
    insertion order (all existing entries shift one position toward
    the eviction boundary).
  - self.recent_events does not grow beyond its fixed capacity.
  - No value other than recent_events of self is modified.

---

### Actual Behavior

The recent_events deque now has at its front (index 0) the tuple (when, stage, status, summary), where when is ts.strftime("%H:%M:%S") if ts is not None else "". If the deque was at maximum capacity before the operation, the oldest element (the rightmost) has been removed; otherwise its size has increased by one. All other attributes of self remain unchanged. Formally, let L be the previous length of recent_events and M be its fixed maximum capacity. Then len(recent_events) = min(L+1, M). recent_events[0] = (when, stage, status, summary). For 1 <= i < min(L+1, M), recent_events[i] = old recent_events[i-1]. All other parts of self's state are preserved.

---

## Code Evidence

Line 2:         when = ts.strftime("%H:%M:%S") if ts else ""

---

## Trigger Condition

The specification requires that when_str be the formatted string if ts is not None, regardless of its truth value. The code uses 'if ts', which treats any falsy nonNone object as None and produces an empty string, violating the spec for ts values that are not None but evaluate to False.

---

## How to trigger the bug

The bug manifests when `_push_recent` is called with a `ts` argument that is not `None` but evaluates to `False` in a boolean context. The code uses `if ts` (truthiness check) instead of `if ts is not None` (identity check), so a falsy non-None datetime-like object will produce an empty `when_str` instead of a properly formatted time string.

### Inputs

| Parameter | Value |
|---|---|
| `self` | A `State` instance with initialized `recent_events` deque |
| `ts` | A custom falsy datetime-like object that has `.strftime()` method but `__bool__()` returns `False` |
| `stage` | `"test_stage"` |
| `status` | `"success"` |
| `summary` | `"test summary"` |

### Expected (spec-correct) Output

`"12:34:56"` (the formatted string from `ts.strftime("%H:%M:%S")`, since `ts is not None`)

### Actual (buggy) Output

`""` (empty string, because `if ts` evaluates to `False` and the code falls through to the `else` branch)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dashboard

class FalsyDatetime:
    def strftime(self, fmt):
        return "12:34:56"
    def __bool__(self):
        return False

with tempfile.TemporaryDirectory() as tmpdir:
    state = dashboard.State(tmpdir)
    state._push_recent(FalsyDatetime(), "test_stage", "success", "test summary")
    when_str, _, _, _ = state.recent_events[0]
    print(when_str)  # actual (buggy) output: ""
    # expected (correct) output: "12:34:56"
```

---

## Probe Script

```python
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on the Python path for the entry-point import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import dashboard

    with tempfile.TemporaryDirectory() as tmpdir:
        state = dashboard.State(tmpdir)

        # Create a falsy mock datetime that has strftime() but is falsy
        class FalsyDatetime:
            def strftime(self, fmt):
                return "12:34:56"

            def __bool__(self):
                return False

        fake_ts = FalsyDatetime()

        # Verify preconditions: fake_ts is falsy but not None
        assert fake_ts is not None, "precondition failed: fake_ts is not None"
        assert not fake_ts, "precondition failed: fake_ts is falsy"

        # Call _push_recent with the falsy non-None datetime
        state._push_recent(fake_ts, "test_stage", "success", "test summary")

        when_str, stage, status, summary = state.recent_events[0]

        # Spec says: when_str = ts.strftime("%H:%M:%S") since ts is not None
        # Code does: when_str = "" because `if ts` is False
        expected = "12:34:56"
        actual = when_str
        passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: '' | expected: '12:34:56'
```
