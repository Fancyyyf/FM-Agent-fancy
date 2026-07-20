# Bug Report: main

**Source file:** `dashboard.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If the trace directory expected under the project directory does not exist,
    a diagnostic message and a waiting hint are written to stderr; execution
    continues regardless.
  - Enters an infinite loop. On each iteration:
      - The dashboard state is refreshed with the latest trace events, OpenCode
        trace data, and bug validation results from the filesystem.
      - A full-screen terminal UI is rendered showing the current aggregated
        dashboard state, refreshed at a rate no slower than once per second
        and no faster than the configured refresh interval.
      - The loop sleeps for the configured refresh interval (default 1.5
        seconds) after each render.
  - On KeyboardInterrupt, the loop terminates and the function returns without
    propagating the exception.

---

### Actual Behavior

The loop calls `time.sleep(args.refresh)` directly, using the `--refresh` CLI argument value as the sleep duration. When `--refresh` is set to a value greater than 1.0 (e.g., 2.0), the loop sleeps for 2.0 seconds between renders, yielding a refresh rate of 0.5 Hz — slower than the spec-mandated minimum of once per second (1 Hz). The `Live` context manager's `refresh_per_second` parameter is set to `max(1.0, 1.0 / args.refresh)`, which correctly computes a minimum refresh rate, but the actual rendering loop is gated by `time.sleep(args.refresh)` which bypasses that safeguard and controls the true refresh cadence.

---

## Code Evidence

Line 21: time.sleep(args.refresh)

---

## Trigger Condition

The specification requires the terminal UI to refresh at a rate no slower than once per second. When --refresh is set to a value greater than 1.0 (e.g., 2.0), the loop sleeps for args.refresh seconds between renders, resulting in a refresh rate of 0.5 Hz, which is slower than once per second. This violates the specified minimum refresh rate.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any valid filesystem path (e.g., `/tmp/test`) |
| `--refresh` | `2.0` (any value > 1.0 triggers the violation) |

### Expected (spec-correct) Output

Sleep duration ≤ 1.0s per iteration, ensuring refresh rate ≥ 1 Hz (no slower than once per second). The loop should sleep for at most 1.0 seconds regardless of the `--refresh` value.

### Actual (buggy) Output

Sleep duration = `args.refresh` (e.g., 2.0s when `--refresh 2.0`), yielding a refresh rate of 0.5 Hz — slower than the spec-minimum of 1 Hz.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.argv = ['dashboard.py', '/tmp/test', '--refresh', '2.0']
import dashboard

# The main() function will parse --refresh=2.0 and call time.sleep(2.0)
# between renders instead of capping sleep at 1.0.
# dashboard.main()
# actual (buggy) sleep duration: 2.0s
# expected (correct) sleep duration: ≤ 1.0s
```

---

## Probe Script

```python
import os
import sys
import time as time_module
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add repo root to sys.path so `import dashboard` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

sys.argv = ['dashboard.py', '/tmp/nonexistent_test_dir', '--refresh', '2.0']

sleep_calls = []

def mock_sleep(duration):
    sleep_calls.append(duration)
    raise KeyboardInterrupt()

time_module.sleep = mock_sleep

try:
    import dashboard

    mock_state = MagicMock()
    mock_state.trace_dir.exists.return_value = False
    mock_state.elapsed.return_value = None

    with patch.object(dashboard, 'State', return_value=mock_state):
        with patch.object(dashboard, 'Console'):
            with patch.object(dashboard, 'Live'):
                with patch.object(dashboard, 'build_layout', return_value=MagicMock()):
                    dashboard.main()
except KeyboardInterrupt:
    pass
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

spec_max_sleep = 1.0  # spec: "no slower than once per second" → sleep ≤ 1.0

if not sleep_calls:
    print('ERROR: time.sleep was never called')
    sys.exit(1)

actual_sleep = sleep_calls[0]
bug_present = actual_sleep > spec_max_sleep

if bug_present:
    print(f'CONFIRMED — time.sleep called with {actual_sleep}s, spec requires ≤ {spec_max_sleep}s')
else:
    print(f'NOT CONFIRMED — time.sleep called with {actual_sleep}s, within spec limit of {spec_max_sleep}s')
```

### Probe Output

```
trace dir not found: <MagicMock name='mock.trace_dir' id='130861804177456'>
Has the pipeline started yet? (waiting…)
CONFIRMED — time.sleep called with 2.0s, spec requires ≤ 1.0s
```

---

