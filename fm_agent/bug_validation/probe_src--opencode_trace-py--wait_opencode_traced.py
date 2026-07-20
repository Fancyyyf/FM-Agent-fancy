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
