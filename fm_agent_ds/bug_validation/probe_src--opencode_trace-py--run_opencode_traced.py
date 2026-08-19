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
