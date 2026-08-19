# Bug Report: run_opencode_traced

**Source file:** `src/opencode_trace-py/run_opencode_traced.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the subprocess exits with code 0 and no error: returns a subprocess.CompletedProcess with returncode=0. When the subprocess exits with a non-zero code or an error occurs: raises subprocess.CalledProcessError whose returncode equals the subprocess exit code. In every execution path (success, failure, or exception), exactly one structured event record is appended atomically to events.jsonl under the trace directory derived from work_dir. The recorded event contains: a unique event_id, the stage label, ISO 8601 start and end timestamps covering the full execution window, the full command list, the process exit code, a status of "success" (exit_code=0 and no error) or "error" (exit_code≠0 or error present), the provided function_ids, input_files, output_files, summary, error, and metadata values, and paths to the corresponding opencode log and trace files. All background threads (log streaming and stdin feeding) are joined and terminated before this function returns normally or propagates an exception.

---

### Actual Behavior

After the execution of run_opencode_traced, regardless of whether it returns normally or raises an exception, the following holds. An event identifier event_id of the form "opencode_<hex_uuid>" has been generated and two ISO 8601 UTC timestamps started and ended have been captured with ended >= started. The call record_opencode_call(work_dir=work_dir, event_id=event_id, stage=stage, status='success' if exit_code == 0 else 'error', started=started, ended=ended, command=command, function_ids=function_ids, input_files=input_files, output_files=output_files, exit_code=exit_code, summary=summary, error=error, metadata=metadata, opencode_log_path=_opencode_log_path(work_dir, event_id), opencode_trace_path=_opencode_trace_path(work_dir, event_id)) has been executed exactly once, atomically appending the corresponding JSON event record to events.jsonl in the trace directory derived from work_dir. The values of exit_code and error reflect the final outcome: if _wait_opencode_process set exit_code and error, exit_code is the integer process exit code and error is a string or None; if a subprocess.CalledProcessError was raised, exit_code is exc.returncode and error is error or str(exc); otherwise exit_code remains 0 and error None. Any non-None log_thread or stdin_thread has been joined (if alive in the finally block, they are waited for completion), ensuring the log file at opencode_log_path is fully written and closed. If _start_opencode_process completed without raising an exception, the subprocess proc has terminated and its exit code is reflected. The function either returns normally with a subprocess.CompletedProcess instance whose args are command_argv(command) and returncode is exit_code (always 0 in this case), or it propagates an exception, which is always a subprocess.CalledProcessError when error or nonzero exit_code was detected, or any other exception produced by the subprocess management.

---

## Code Evidence

Line 45:             status="success" if exit_code == 0 else "error",

---

## Trigger Condition

The code determines the event status solely by comparing exit_code to 0. The specification requires status 'error' whenever exit_code≠0 or an error is present. Here the process exits with code 0 but _wait_opencode_process reports an error string, so status should be 'error', not 'success'.

---

## How to trigger the bug

The bug occurs in the `finally` block of `run_opencode_traced` when `record_opencode_call` is invoked. The status is determined by `exit_code == 0` alone, ignoring the `error` variable. When the subprocess exits with code 0 (success) but `_wait_opencode_process` simultaneously reports a non-None error string (e.g., a timeout, an OpenCode internal failure, or a resource exhaustion message), the specification requires `status="error"` (because an error is present), but the code produces `status="success"` (because `exit_code == 0`). This means a failing OpenCode invocation can be incorrectly recorded as successful in the trace.

Notably, the companion function `finish_opencode_trace` (same file, line 416) correctly implements the specification: `status = "error" if record.error or record.proc.returncode != 0 else "success"`.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/probe-proj` |
| work_dir | `<temporary directory>` |
| command | `["opencode", "run", "--test"]` |
| stage | `"test-stage"` |
| _wait_opencode_process return | `(0, "mock error: something went wrong during execution")` |

### Expected (spec-correct) Output

`record_opencode_call` is called with `status="error"` (because error is present, even though exit_code is 0).

### Actual (buggy) Output

`record_opencode_call` is called with `status="success"` (because exit_code is 0, ignoring the error).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path.cwd()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

tmpdir = tempfile.mkdtemp()
captured = {}

def fake_wait(proc, command, stage):
    return 0, "mock error: something went wrong"

def fake_start(proj_dir, work_dir, event_id, command, log_path):
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_log = MagicMock(spec=threading.Thread)
    mock_stdin = MagicMock(spec=threading.Thread)
    mock_log.is_alive.return_value = False
    mock_stdin.is_alive.return_value = False
    return mock_proc, mock_log, mock_stdin

with patch("src.opencode_trace.record_opencode_call",
           side_effect=lambda **kw: captured.update(kw)), \
     patch("src.opencode_trace._wait_opencode_process", side_effect=fake_wait), \
     patch("src.opencode_trace._start_opencode_process", side_effect=fake_start), \
     patch("src.opencode_trace.new_event_id", return_value="test-id"), \
     patch("src.opencode_trace.utc_now_iso", return_value="2024-01-01T00:00:00Z"), \
     patch("src.opencode_trace._opencode_log_path", return_value="/tmp/a.log"), \
     patch("src.opencode_trace._opencode_trace_path", return_value="/tmp/b.jsonl"), \
     patch("src.opencode_trace.command_argv", return_value=["test"]):
    from src.opencode_trace import run_opencode_traced
    try:
        run_opencode_traced("/tmp", tmpdir, ["cmd"], "stage")
    except subprocess.CalledProcessError:
        pass
    print(f"status={captured.get('status')!r}")
    # actual (buggy) output: 'success'
    # expected (correct) output: 'error'
```

---

## Probe Script

```python
"""Probe for bug: run_opencode_traced uses exit_code alone to determine
event status, ignoring the error variable. When exit_code is 0 but error is
present (e.g. the process exits cleanly but _wait_opencode_process reports
an error), status should be 'error', not 'success'.

Bug ID: src--opencode_trace-py--run_opencode_traced
"""

import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Save and sanitize environment to isolate the test
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL", "LLM_MODEL",
    "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

tmpdir = tempfile.mkdtemp(prefix="probe_run_opencode_traced_")

# Captured kwargs from the patched record_opencode_call
captured: dict = {}

def _capture_record_opencode(**kwargs):
    """Replace record_opencode_call; capture all keyword arguments."""
    captured.clear()
    captured.update(kwargs)

def _fake_wait_opencode_process(proc, command, stage):
    """Simulate a process that exits with code 0 BUT reports an error string."""
    return 0, "mock error: something went wrong during execution"

def _fake_start_opencode_process(proj_dir, work_dir, event_id, command, opencode_log_path):
    """Return a mock process with finished threads."""
    mock_proc = MagicMock(spec=subprocess.Popen)
    mock_log = MagicMock(spec=threading.Thread)
    mock_stdin = MagicMock(spec=threading.Thread)
    mock_log.is_alive.return_value = False
    mock_stdin.is_alive.return_value = False
    return mock_proc, mock_log, mock_stdin

try:
    # Patch all dependencies BEFORE importing the module so the function's
    # __globals__ reference our mocks at call time.
    with patch("src.opencode_trace.record_opencode_call", side_effect=_capture_record_opencode), \
         patch("src.opencode_trace._wait_opencode_process", side_effect=_fake_wait_opencode_process), \
         patch("src.opencode_trace._start_opencode_process", side_effect=_fake_start_opencode_process), \
         patch("src.opencode_trace.new_event_id", return_value="probe-test-event-id"), \
         patch("src.opencode_trace.utc_now_iso", return_value="2024-01-01T00:00:00Z"), \
         patch("src.opencode_trace._opencode_log_path", return_value="/tmp/probe-opencode.log"), \
         patch("src.opencode_trace._opencode_trace_path", return_value="/tmp/probe-opencode.jsonl"), \
         patch("src.opencode_trace.command_argv", return_value=["opencode", "run", "--test"]):

        from src.opencode_trace import run_opencode_traced

        try:
            run_opencode_traced(
                proj_dir="/tmp/probe-proj",
                work_dir=tmpdir,
                command=["opencode", "run", "--test"],
                stage="test-stage",
            )
            # We should not reach here — function must raise CalledProcessError
            # when error is set (line 326: `if error: raise`)
            actual_status = captured.get("status")
            actual_error = captured.get("error")
            actual_code = captured.get("exit_code")
            expected_status = "error"

            if actual_status != expected_status:
                print(
                    f"CONFIRMED — function returned normally but "
                    f"status={actual_status!r}, expected={expected_status!r}; "
                    f"exit_code={actual_code!r}, error={actual_error!r}. "
                    f"Bug: status based solely on exit_code==0, ignoring "
                    f"non-None error string."
                )
            else:
                print(
                    f"NOT CONFIRMED — "
                    f"status={actual_status!r} matches expected, "
                    f"exit_code={actual_code!r}, error={actual_error!r}"
                )

        except subprocess.CalledProcessError:
            # Expected path — the function raises on error (line 326)
            actual_status = captured.get("status")
            actual_error = captured.get("error")
            actual_code = captured.get("exit_code")
            expected_status = "error"

            if actual_status != expected_status:
                print(
                    f"CONFIRMED — record_opencode_call received "
                    f"status={actual_status!r}, expected={expected_status!r}. "
                    f"Bug: status='success' despite error={actual_error!r} "
                    f"and exit_code={actual_code!r}. "
                    f"The status logic only checks exit_code==0, "
                    f"ignoring the error parameter."
                )
            else:
                print(
                    f"NOT CONFIRMED — "
                    f"status={actual_status!r} matches expected={expected_status!r}, "
                    f"error={actual_error!r}, exit_code={actual_code!r}"
                )

        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"ERROR: unexpected exception: {type(exc).__name__}: {exc}")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

    # Clean up temp directory
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — record_opencode_call received status='success', expected='error'. Bug: status='success' despite error='mock error: something went wrong during execution' and exit_code=0. The status logic only checks exit_code==0, ignoring the error parameter.
```
