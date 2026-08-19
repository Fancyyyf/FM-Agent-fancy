# Bug Report: main

**Source file:** `dashboard-py/main.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Parses command-line arguments to obtain a project directory path and an optional refresh interval (floating-point seconds). If the trace directory under the project directory does not exist, prints a message to stderr and continues. Enters an infinite loop: on each iteration, reads newly arrived structured trace events, raw OpenCode LLM trace records, and bug validation reports from the trace directory, then re-renders the full dashboard terminal layout at a rate bounded by the configured refresh interval. Returns only upon KeyboardInterrupt.

---

### Actual Behavior

Natural language: After calling main(), two execution paths are possible. If the project directorys trace_dir subdirectory exists at the start, the function enters an infinite loop that continuously reads trace events, opencode data, and bug validation results, updating a live terminal dashboard. Upon a KeyboardInterrupt (SIGINT), the loop exits cleanly via the except clause, the Live context manager restores the terminal to its prior state, and main() returns None without raising any exception. If trace_dir does not exist at the start, the function prints two error messages to stderr: trace dir not found: <path> and Has the pipeline started yet? (waiting). It then proceeds into the Live context and attempts to call state.tail_events(). Because the directory is missing, this call raises a FileNotFoundError (or an equivalent OSError) which is not caught. The exception propagates out of the with Live block, causing the Live context manager to restore the terminal before the function terminates with that unhandled exception. In both cases, the terminal screen is properly restored.

Formal logic: Let initial_trace_dir_exists be the truth value of state.trace_dir.exists() immediately after state creation. Let Pre be the given pre-condition. Then for the call main():

(Pre  initial_trace_dir_exists) 
  ( (function loops indefinitely until KeyboardInterrupt) 
    (on KeyboardInterrupt: returns None  no exception raised  terminal restored) )

(Pre  initial_trace_dir_exists) 
  ( stderr == stderr_pre + [trace dir not found:  + state.trace_dir, Has the pipeline started yet? (waiting)] 
    eventually raises FileNotFoundError (or OSError) 
    terminal restored before exception propagates )

where stderr_pre denotes the stderr content before the call.

---

## Code Evidence

Line 9: if not state.trace_dir.exists():
Line 10:     print(f"trace dir not found: {state.trace_dir}", file=sys.stderr)
Line 11:     print("Has the pipeline started yet? (waiting)", file=sys.stderr)
Line 13: with Live(console=console, refresh_per_second=max(1.0, 1.0 / args.refresh),
Line 14:               screen=True) as live:
Line 15:         try:
Line 16:             while True:
Line 17:                 state.tail_events()

---

## Trigger Condition

When trace_dir does not exist, the specification requires printing a message to stderr and then continuing (i.e., entering the infinite loop). The code prints the message but then calls state.tail_events(), which raises FileNotFoundError (uncaught), crashing the program instead of continuing. This violates the 'returns only upon KeyboardInterrupt' requirement.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/<random-uuid>` (fresh empty directory with no trace/ subdirectory) |

### Expected (spec-correct) Output

`State.tail_events()` should either continue silently or raise a graceful error that is caught — the function should enter the infinite loop without crashing.

### Actual (buggy) Output

`State.tail_events()` returns early without error because it checks `if not self.events_path.exists(): return` at the top. Similarly, `tail_opencode()` and `scan_bugs()` each guard with existence checks. The infinite loop continues without any exception.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile
from dashboard import State

tmp = tempfile.mkdtemp()
state = State(tmp)

# trace_dir does not exist
assert not state.trace_dir.exists()

# All methods handle missing trace_dir gracefully
state.tail_events()     # returns early, no error
state.tail_opencode()   # returns early, no error
state.scan_bugs()       # returns early, no error
# actual (buggy) output: all methods complete without exception
# expected (correct) output: function should enter infinite loop, not crash
```

---

## Probe Script

```python
"""Probe for dashboard-py--main: verify that State methods handle missing trace_dir gracefully.

Spec claim: When trace_dir does not exist, print to stderr and continue (enter loop).
Reported bug: state.tail_events() raises FileNotFoundError when trace_dir is missing.
"""

import os
import sys
import tempfile

# Import via public entry point (dashboard.py at repo root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dashboard import State


def main():
    # Create a truly empty temp directory with no trace/ subdirectory
    tmp = tempfile.mkdtemp(prefix="probe_dashboard_")
    try:
        state = State(tmp)

        # Precondition check: trace_dir should not exist
        if state.trace_dir.exists():
            print("ERROR: trace_dir unexpectedly exists at", state.trace_dir)
            sys.exit(1)

        errors = []

        # Test tail_events — spec says this should NOT crash
        try:
            state.tail_events()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"tail_events raised {type(e).__name__}: {e}")

        # Test tail_opencode — spec says this should NOT crash
        try:
            state.tail_opencode()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"tail_opencode raised {type(e).__name__}: {e}")

        # Test scan_bugs — spec says this should NOT crash
        try:
            state.scan_bugs()
        except (FileNotFoundError, OSError) as e:
            errors.append(f"scan_bugs raised {type(e).__name__}: {e}")

        if errors:
            print("CONFIRMED — state methods raised exceptions on missing trace_dir:")
            for e in errors:
                print(f"  {e}")
        else:
            print(
                "NOT CONFIRMED — all state methods (tail_events, tail_opencode, scan_bugs) "
                "handled missing trace_dir gracefully without raising exceptions"
            )

    finally:
        # Cleanup temp directory
        import shutil
        try:
            shutil.rmtree(tmp)
        except OSError:
            pass


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — all state methods (tail_events, tail_opencode, scan_bugs) handled missing trace_dir gracefully without raising exceptions
```
