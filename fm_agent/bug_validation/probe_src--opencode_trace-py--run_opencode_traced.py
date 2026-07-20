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
