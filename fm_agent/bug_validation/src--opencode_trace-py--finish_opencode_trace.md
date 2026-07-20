# Bug Report: finish_opencode_trace

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If record.stdin_thread is not None, that thread has been joined (it is guaranteed completed before this function returns)
- If record.log_thread is not None, that thread has been joined (it is guaranteed completed before this function returns)
- A trace event of type "opencode_call" has been recorded in the trace database under record.work_dir
- The recorded event's status is "success" if and only if record.error is falsy AND record.proc.returncode == 0; otherwise the status is "error"
- The recorded event's end_time is the current UTC time at the moment of recording, formatted as ISO 8601
- The recorded event preserves the following fields from record unchanged: event_id, stage, started, command, function_ids, input_files, output_files, summary, error, metadata, opencode_log_path, opencode_trace_path, and exit_code

---

### Actual Behavior

After normal execution (no uncaught exception) of finish_opencode_trace(record), the following hold:
1. Thread joining: (record.stdin_thread != None)  record.stdin_thread.join() has completed, guaranteeing the thread has terminated. (record.log_thread != None)  record.log_thread.join() has completed, guaranteeing that thread has terminated.
2. Trace recording: A trace event has been appended to the trace events JSONL file under record.work_dir, with the exact fields:
   - work_dir = record.work_dir
   - event_id = record.event_id
   - stage = record.stage
   - status = "error" if (record.error or record.proc.returncode != 0) else "success"
   - started = record.started
   - ended = utc_now_iso() (current UTC timestamp in ISO8601)
   - command = record.command
   - function_ids = record.function_ids
   - input_files = record.input_files
   - output_files = record.output_files
   - exit_code = record.proc.returncode
   - summary = record.summary
   - error = record.error
   - metadata = record.metadata
   - opencode_log_path = record.opencode_log_path
   - opencode_trace_path = record.opencode_trace_path
3. The record object remains otherwise unmodified. The preconditions of record_opencode_call are satisfied (work_dir writable, event_id nonempty, status is exactly "success" or "error", started  ended).

If an exception is raised at any point (e.g. in join or record_opencode_call), the function terminates abruptly. In this case the postcondition may not hold; the trace event may be missing or partially written, and the thread joins may not have been executed depending on the exception location.

---

## Code Evidence

Line 7: record_opencode_call(...)

---

## Trigger Condition

The code does not ensure that the trace event is recorded. If record.work_dir is not a writable directory, record_opencode_call will raise an exception and the trace event will not be appended, violating the specification requirement that a trace event has been recorded.

---

## How to trigger the bug

The bug occurs when `finish_opencode_trace()` is called with a `TracedOpenCodeProcess` record whose `work_dir` is a non-writable directory. The call to `record_opencode_call()` propagates through to `os.makedirs()` inside `_ensure_trace_dirs()`, which raises a `PermissionError`. Since `finish_opencode_trace()` does not catch this exception, it propagates unhandled, and the trace event is never recorded — violating the post-condition that "A trace event of type opencode_call has been recorded in the trace database under record.work_dir."

### Inputs

| Parameter | Value |
|-----------|-------|
| `record.work_dir` | A directory with no write permission (e.g., mode 0o500) |
| `record.proc` | A completed `subprocess.Popen` (returncode == 0) |
| `record.event_id` | `"test_event_001"` |
| `record.stage` | `"spec"` |
| `record.started` | `"2025-01-01T00:00:00Z"` |
| `record.command` | `["opencode", "run", "--stage", "spec"]` |
| `record.error` | `None` |
| `record.stdin_thread` | `None` |
| `record.log_thread` | `None` |

### Expected (spec-correct) Output

The trace event should be recorded in `<work_dir>/trace/events.jsonl` regardless of filesystem permissions. The function should either ensure the directory is writable before calling `record_opencode_call` or handle the exception and still record the event through an alternative mechanism.

### Actual (buggy) Output

A `PermissionError` is raised by `os.makedirs()` inside `_ensure_trace_dirs()`, propagated through `record_trace_event()` → `record_opencode_call()` → `finish_opencode_trace()`. The trace event is **not** recorded. The `trace/` directory and `events.jsonl` file do not exist under `record.work_dir`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import subprocess
import tempfile
import os
from src.opencode_trace import finish_opencode_trace, TracedOpenCodeProcess

proc = subprocess.Popen(["true"])
proc.wait()

work_dir = tempfile.mkdtemp(prefix="fm_agent_probe_")
os.chmod(work_dir, 0o500)  # make read-only

record = TracedOpenCodeProcess(
    proc=proc,
    work_dir=work_dir,
    event_id="test_event_001",
    stage="spec",
    started="2025-01-01T00:00:00Z",
    command=["opencode", "run", "--stage", "spec"],
    function_ids=["test::func"],
    input_files=[],
    output_files=[],
    summary="test summary",
    metadata={},
    opencode_log_path=None,
    opencode_trace_path=None,
    log_thread=None,
    stdin_thread=None,
    error=None,
)

finish_opencode_trace(record)
# Raises PermissionError — trace event NOT recorded
# actual (buggy) output: PermissionError exception, no events.jsonl created
# expected (correct) output: trace event recorded in work_dir/trace/events.jsonl
```

---

## Probe Script

```python
import sys
import os
import subprocess
import tempfile
import shutil

try:
    from src.opencode_trace import finish_opencode_trace, TracedOpenCodeProcess

    # Create a completed subprocess (returncode is set)
    proc = subprocess.Popen(["true"])
    proc.wait()

    # Create a temp directory and make it read-only so os.makedirs
    # cannot create trace/ subdirectories inside it
    work_dir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    os.chmod(work_dir, 0o500)  # r-x------ (no write)

    record = TracedOpenCodeProcess(
        proc=proc,
        work_dir=work_dir,
        event_id="test_event_001",
        stage="spec",
        started="2025-01-01T00:00:00Z",
        command=["opencode", "run", "--stage", "spec"],
        function_ids=["test::func"],
        input_files=[],
        output_files=[],
        summary="test summary",
        metadata={},
        opencode_log_path=None,
        opencode_trace_path=None,
        log_thread=None,
        stdin_thread=None,
        error=None,
    )

    exception_raised = False
    try:
        finish_opencode_trace(record)
    except (FileNotFoundError, OSError, PermissionError):
        exception_raised = True

    # Restore write permission so we can check/clean up
    os.chmod(work_dir, 0o700)

    # Spec says: "A trace event of type opencode_call has been recorded
    # in the trace database under record.work_dir"
    events_path = os.path.join(work_dir, "trace", "events.jsonl")
    trace_recorded = os.path.exists(events_path)

    bug_confirmed = exception_raised and not trace_recorded

    if bug_confirmed:
        print(
            f"CONFIRMED — exception raised: {exception_raised}, "
            f"trace recorded: {trace_recorded} | "
            f"spec requires trace event to be recorded, but "
            f"finish_opencode_trace does not handle exceptions from "
            f"record_opencode_call, so a non-writable work_dir prevents "
            f"recording"
        )
    else:
        print(
            f"NOT CONFIRMED — exception raised: {exception_raised}, "
            f"trace recorded: {trace_recorded}"
        )

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — exception raised: True, trace recorded: False | spec requires trace event to be recorded, but finish_opencode_trace does not handle exceptions from record_opencode_call, so a non-writable work_dir prevents recording
```
