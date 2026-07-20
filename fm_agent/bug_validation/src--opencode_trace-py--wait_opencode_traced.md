# Bug Report: wait_opencode_traced

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If an empty or None error string is produced during waiting and record.error is None,
    record.error remains None.

---

### Actual Behavior

After execution, the function returns the integer exit_code obtained from `_wait_opencode_process`. The `record.proc` subprocess has been waited on and is no longer running; its `returncode` is set to the same exit_code value (the process's exit code, or the negative of the signal number if killed by a signal). The `record.error` attribute is updated as follows: if the error string from `_wait_opencode_process` is not None, then `record.error` becomes that string; otherwise `record.error` retains its previous value (which may be None or a prior error). The other attributes of `record` (`command`, `stage`) are unchanged. No exceptions are raised.

Formal logic:
Let old state be unprimed, new state primed.
Let (exit_code, error) = _wait_opencode_process(record.proc, record.command, record.stage, timeout_seconds).
Then:
  result = exit_code
  record.proc' = record.proc (same Popen object)  record.proc'.returncode = exit_code  record.proc'.poll() is not None
  record.error' = if error ≠ None then error else record.error
  record.command' = record.command
  record.stage' = record.stage
  record otherwise unaffected.

---

## Code Evidence

Line 8: `if error or record.error is None:`

---

## Trigger Condition

The condition `error or record.error is None` incorrectly forces an update when an empty error string is produced and record.error is None. The empty string is falsy, so the if-guard becomes True because record.error is None, leading to record.error being assigned the empty string. The specification explicitly states that when an empty or None error string is produced and record.error is None, record.error must remain None.

---

## How to trigger the bug

The guard condition `if error or record.error is None:` on line 333 of `src/opencode_trace.py` uses a boolean OR. When `_wait_opencode_process` returns an empty string `""` for the error and `record.error` is `None`, Python evaluates `"" or True` as `True` because the empty string is falsy. This causes `record.error` to be assigned `""` (empty string), violating the specification which requires `record.error` to remain `None`.

In normal execution, `_wait_opencode_process` returns either `None` (clean exit) or a non-empty timeout message. The bug is dormant during normal operation but represents a correctness violation in the code's logic: if `_wait_opencode_process` were ever to return an empty error string, the guard would incorrectly overwrite `record.error`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `record` | `TracedOpenCodeProcess` with `record.error = None` |
| `timeout_seconds` | `999` |
| `_wait_opencode_process` return | `(0, "")` — exit_code=0, error="" (empty string, monkey-patched) |

### Expected (spec-correct) Output

`record.error` remains `None`

### Actual (buggy) Output

`record.error` is set to `""` (empty string)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import wait_opencode_traced, TracedOpenCodeProcess
import src.opencode_trace as ot_module
import subprocess

# Monkey-patch _wait_opencode_process to return empty error string
original = ot_module._wait_opencode_process
ot_module._wait_opencode_process = lambda *a, **kw: (0, "")

record = TracedOpenCodeProcess(
    proc=subprocess.Popen(["true"]),
    work_dir="/tmp",
    event_id="test",
    stage="test",
    started="2025-01-01T00:00:00Z",
    command=["opencode", "run"],
)
record.proc.wait()

wait_opencode_traced(record, timeout_seconds=999)
# actual (buggy) output: record.error == ''
# expected (correct) output: record.error is None

ot_module._wait_opencode_process = original
```

---

## Probe Script

```python
import sys
import os
import subprocess
import threading

# Ensure the repo root is on sys.path so "src" is importable.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/../.."))

original = None

try:
    from src.opencode_trace import wait_opencode_traced, TracedOpenCodeProcess
    import src.opencode_trace as ot_module

    # Monkey-patch _wait_opencode_process to return an empty error string.
    # _wait_opencode_process never returns "" in normal operation, but the
    # specification explicitly covers the empty-string case, and wait_opencode_traced
    # is supposed to handle it correctly.
    original = ot_module._wait_opencode_process

    def mock_wait_opencode_process(proc, command, stage, timeout_seconds):
        return (0, "")  # exit_code=0, error="" empty string

    ot_module._wait_opencode_process = mock_wait_opencode_process

    # Create a dummy completed subprocess (proc won't be used since we patched)
    proc = subprocess.Popen(["true"])
    proc.wait()

    record = TracedOpenCodeProcess(
        proc=proc,
        work_dir="/tmp",
        event_id="test_event_wait",
        stage="test",
        started="2025-01-01T00:00:00Z",
        command=["opencode", "run"],
    )

    # record.error should be None initially (default)
    assert record.error is None, f"Expected record.error to be None, got {record.error!r}"

    exit_code = wait_opencode_traced(record, timeout_seconds=999)

    # SPEC claim: If an empty or None error string is produced during waiting
    # and record.error is None, record.error remains None.
    # BUG: record.error is set to "" instead of staying None.
    expected = None
    actual = record.error
    bug_reproduced = actual != expected

    if bug_reproduced:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Restore original
    ot_module._wait_opencode_process = original
```

### Probe Output

```
CONFIRMED — actual: '' | expected: None
```
