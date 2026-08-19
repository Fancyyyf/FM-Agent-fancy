import sys
import os
import subprocess
import tempfile

# Add repo root to path so package imports resolve.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

# Create a fresh temp dir for the probe workspace (FM-Agent self-validation guard).
probe_tmp = tempfile.mkdtemp(prefix="probe_wait_opencode_")

# ---------------------------------------------------------------------------
# Mock subprocess.Popen that simulates:
#   1. Initial wait(timeout=...) raises TimeoutExpired
#   2. terminate() is called, then wait(timeout=10) returns 0
#      (process exited cleanly via SIGTERM — NOT SIGKILL)
#   3. kill() is never reached because the process exits within the grace period
#
# Trigger condition: exit code 0 after SIGTERM-only gets mapped to -15.
# Spec claim:  -15 mapping only after SIGKILL (forced termination).
# ---------------------------------------------------------------------------
class MockPopen:
    def __init__(self):
        self._terminated = False
        self.returncode = None

    def wait(self, timeout=None):
        if not self._terminated:
            raise subprocess.TimeoutExpired(cmd=["mock_cmd"], timeout=timeout or 1)
        self.returncode = 0
        return 0

    def terminate(self):
        self._terminated = True

    def kill(self):
        # Should not be reached in this scenario.
        self._terminated = True

# Import the public API (entry-point rule).
from src.opencode_trace import wait_opencode_traced, TracedOpenCodeProcess

try:
    mock_proc = MockPopen()

    record = TracedOpenCodeProcess(
        proc=mock_proc,
        work_dir=probe_tmp,
        event_id="test_wait_opencode",
        stage="test",
        started="2025-01-01T00:00:00Z",
        command=["echo", "hello"],
    )

    exit_code = wait_opencode_traced(record, timeout_seconds=1)

    # Per spec: SIGTERM with exit code 0 should return 0 (not -15).
    # The -15 remapping should only happen after SIGKILL.
    expected = 0
    passed = exit_code != expected  # True -> bug reproduced (got -15)

    if passed:
        print(f"CONFIRMED — actual: {exit_code!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {exit_code!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
