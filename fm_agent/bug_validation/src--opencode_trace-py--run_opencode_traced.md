# Bug Report: run_opencode_traced

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/opencode_trace-py/run_opencode_traced.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Launches command as a subprocess with work_dir as the working directory
    and waits for it to complete, subject to a configured timeout
  - If the subprocess exits with code 0: returns a CompletedProcess
    containing the command argv and exit code
  - If the subprocess exits with a non-zero code, or if the configured
    timeout expires: raises subprocess.CalledProcessError whose returncode
    reflects the actual exit code (non-zero exit) or a synthetic non-zero
    code (timeout)
  - In every exit path  success, non-zero exit, or timeout  writes
    exactly one structured trace event as a JSON line appended to
    fm_agent/trace/events.jsonl
  - The trace event includes the event ID, stage name, start and end
    timestamps in ISO 8601 UTC, status ("success" for exit code 0,
    "error" otherwise), the full command, function IDs, input and output
    file lists, exit code, summary, error description when the outcome is
    a failure, and metadata
  - When a failure (non-zero exit or timeout) occurs, the trace event is
    written before the CalledProcessError propagates, guaranteeing that
    every invocation is recorded regardless of outcome
  - All subprocess output-capture background threads are joined before the
    function returns or raises, ensuring no dangling threads

---

### Actual Behavior

After execution of run_opencode_traced, regardless of whether it returns normally, raises subprocess.CalledProcessError, or raises any other exception, the following global conditions hold:

1. A uniquely identified opencode subprocess was launched. Any log-capture thread (log_thread) and stdin-handling thread (stdin_thread) that were started have been joined (blocking until they finish), so no orphaned threads remain.

2. A trace event record is appended to the file at {work_dir}/fm_agent/trace/events.jsonl via record_opencode_call. The recorded fields are:
   - work_dir: the given work_dir
   - event_id: a globally unique string returned by new_event_id("opencode")
   - stage: the given stage
   - status: "success" if the exit_code variable at the time of recording equals 0, otherwise "error"
   - started: an ISO 8601 UTC timestamp taken before subprocess launch
   - ended: an ISO 8601 UTC timestamp taken inside the finally block
   - command: the original command list
   - exit_code: the value of the exit_code variable at recording time
   - error: None or a non-empty error string (set only if the subprocess timed out, failed, or a CalledProcessError was raised)
   - function_ids, input_files, output_files, summary, metadata: exactly the input arguments if provided, else their default (None)
   - opencode_log_path: the computed log file path where the subprocess stdout/stderr were written
   - opencode_trace_path: the computed trace file path for raw LLM interactions (content may be empty if not applicable).

3. The exit_code variable reflects the subprocess return code if the subprocess ran; it is 0 initially and may stay 0 if the subprocess never started or wait was not reached (e.g., early exception). The error variable is None unless a CalledProcessError is raised (either because _wait_opencode_process returned a non-None error, or because exit_code != 0), in which case it becomes that error string or the string representation of the exception.

---

## Code Evidence

Line 45: status="success" if exit_code == 0 else "error"

---

## Trigger Condition

The specification requires the trace status to be 'error' for any failure including timeouts. The code sets status to 'success' whenever exit_code == 0, even if a timeout error occurred with exit_code 0. A concrete input where the subprocess times out and the wait function returns (0, error_string) causes the event to be recorded as 'success' while the specification demands 'error'. This violates the requirement that every failure writes an 'error' status event.

---

## How to trigger the bug

When `_wait_opencode_process` returns `(0, error_string)` — i.e., the subprocess exited with code 0 but an error (such as timeout) occurred — the `finally` block records the trace event with `status="success"` because it only checks `exit_code == 0`, ignoring the `error` variable. The specification requires `status="error"` for any failure including timeouts.

Note: In the current implementation, `_wait_opencode_process` has a workaround that forces `exit_code = -15` when a timeout results in exit code 0, masking this bug for the timeout case. However, the underlying logic flaw in `run_opencode_traced` remains — any future code path that produces `(0, error_string)` from the wait function would trigger this bug.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | (repo root) |
| work_dir | (temp directory) |
| command | `["fake_cmd"]` |
| stage | `"test_stage"` |
| _wait_opencode_process return | `(0, "simulated timeout after 1800s")` |

### Expected (spec-correct) Output

`status="error"` — because an error occurred (timeout), regardless of exit_code being 0.

### Actual (buggy) Output

`status="success"` — because the code only checks `exit_code == 0`, ignoring the non-None `error` variable.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, tempfile
sys.path.insert(0, os.getcwd())

import src.opencode_trace as ot

captured_status = None

def fake_record(**kwargs):
    global captured_status
    captured_status = kwargs.get("status")

def fake_start(*args, **kwargs):
    return None, None, None

def fake_wait(*args, **kwargs):
    return (0, "simulated timeout after 1800s")

ot._start_opencode_process = fake_start
ot._wait_opencode_process = fake_wait
ot.record_opencode_call = fake_record

work_dir = tempfile.mkdtemp()
try:
    ot.run_opencode_traced(".", work_dir, ["cmd"], "test")
except ot.subprocess.CalledProcessError:
    pass

print(f"captured_status={captured_status!r}")
# actual (buggy) output: captured_status='success'
# expected (correct) output: captured_status='error'
```

---

## Probe Script

```python
"""Probe script for bug: src--opencode_trace-py--run_opencode_traced

Bug: run_opencode_traced sets trace status="success" when exit_code==0,
ignoring whether an error occurred (e.g. timeout). The spec requires
status="error" for any failure, regardless of exit_code.
"""
import os
import sys
import tempfile

# Ensure repo root is on sys.path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

import src.opencode_trace as ot

# ---- Capture what status is recorded ----
captured_status = None

def _fake_record(**kwargs):
    global captured_status
    captured_status = kwargs.get("status")

def _fake_start(*args, **kwargs):
    """Return (proc, log_thread, stdin_thread) all None to skip subprocess launch."""
    return None, None, None

def _fake_wait(*args, **kwargs):
    """Simulate a timeout where process was killed and returned exit_code 0
    but an error string is present (the scenario before the -15 workaround)."""
    return (0, "simulated timeout after 1800s")

# ---- Save originals ----
_original_start = ot._start_opencode_process
_original_wait = ot._wait_opencode_process
_original_record = ot.record_opencode_call

# ---- Apply patches ----
ot._start_opencode_process = _fake_start
ot._wait_opencode_process = _fake_wait
ot.record_opencode_call = _fake_record

work_dir = tempfile.mkdtemp(prefix="fm_agent_probe_")

try:
    result = ot.run_opencode_traced(
        proj_dir=repo_root,
        work_dir=work_dir,
        command=["fake_cmd"],
        stage="test_stage",
    )
    # Should not get here — error was set, so CalledProcessError should be raised
    print(f"ERROR: unexpected normal return: {result!r}")
    sys.exit(1)
except ot.subprocess.CalledProcessError:
    # Expected: error was set, so CalledProcessError is raised
    pass
except Exception as exc:
    print(f"ERROR: unexpected exception: {exc}")
    sys.exit(1)
finally:
    # Restore originals
    ot._start_opencode_process = _original_start
    ot._wait_opencode_process = _original_wait
    ot.record_opencode_call = _original_record
    # Cleanup temp dir
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)

# ---- Verdict ----
expected = "error"
if captured_status == "success":
    print(
        f"CONFIRMED — actual: status={captured_status!r} "
        f"| expected: status={expected!r} "
        f"(error was set, exit_code was 0)"
    )
else:
    print(
        f"NOT CONFIRMED — actual status: {captured_status!r}"
    )
```

### Probe Output

```
CONFIRMED — actual: status='success' | expected: status='error' (error was set, exit_code was 0)
```
