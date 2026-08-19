# Bug Report: _wait_opencode_process

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Blocks until the process in proc completes or the timeout expires. Returns a 2-tuple (exit_code, error). When the process exits within timeout_seconds: exit_code is the integer process exit code and error is None. When the process does not exit within timeout_seconds: proc is terminated (SIGTERM), then force-killed (SIGKILL) if termination does not complete within a 10-second grace period; exit_code is the process exit code after forced termination, mapped to -15 when that exit code is falsy (0 or None); error is a descriptive string indicating the timeout condition.

---

### Actual Behavior

Upon normal return (no unhandled exception), the function returns a 2-tuple (ec, em) where ec  , em  {None}  {s | s == f'timeout after {timeout_seconds}s'}. The subprocess.Popen instance proc has been reaped: proc.wait() was called (possibly after terminate/kill), so proc.returncode   and the child process is not running. If the initial proc.wait(timeout=timeout_seconds) completed without raising TimeoutExpired (the no-timeout case), then ec = proc.returncode and em = None. If it raised TimeoutExpired (the timeout case), then em = f'timeout after {timeout_seconds}s'. In the timeout case, proc.terminate() was called; if the subsequent proc.wait(timeout=10) raised TimeoutExpired, proc.kill() was called and then proc.wait() without timeout. Finally, ec = proc.returncode unless proc.returncode == 0, in which case ec = -15 (so a killed-on-timeout success is never reported as success). The attribute proc.returncode equals the actual exit status from the last successful wait, which may be 0 even when ec is -15.

---

## Code Evidence

Line 18: if not exit_code:
Line 19:       exit_code = -15  # killed-on-timeout must never record as success

---

## Trigger Condition

The specification maps the exit code to -15 only after forced termination (SIGKILL). The code unconditionally maps any falsy exit code in the timeout path, including when the process exits cleanly via SIGTERM with code 0. This causes a mismatch.

---

## How to trigger the bug

A subprocess that times out, receives SIGTERM, and exits cleanly within the 10-second grace period with exit code 0 will have its exit code incorrectly remapped to -15. The -15 remapping should only apply after SIGKILL (forced termination), not after SIGTERM alone.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proc` | `subprocess.Popen` instance whose first `wait(timeout=...)` raises `TimeoutExpired`, then after `terminate()` returns exit code 0 on `wait(timeout=10)` |
| `command` | `["echo", "hello"]` |
| `stage` | `"test"` |
| `timeout_seconds` | `1` |

### Expected (spec-correct) Output

`(0, "timeout after 1s")` — SIGTERM with clean exit 0 should not be remapped

### Actual (buggy) Output

`(-15, "timeout after 1s")` — the `if not exit_code:` guard fires on any falsy exit code in the timeout path, regardless of whether SIGKILL was actually sent

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.opencode_trace import wait_opencode_traced, TracedOpenCodeProcess
import subprocess

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
        self._terminated = True

record = TracedOpenCodeProcess(
    proc=MockPopen(),
    work_dir="/tmp/test",
    event_id="test",
    stage="test",
    started="2025-01-01T00:00:00Z",
    command=["echo", "hello"],
)
exit_code = wait_opencode_traced(record, timeout_seconds=1)
# actual (buggy) output: -15
# expected (correct) output: 0
```

---

## Probe Script

```python
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
```

### Probe Output

```
WARNING:root:opencode test timed out after 1s, killing: echo hello
CONFIRMED — actual: -15 | expected: 0
```
