# Bug Report: ElpClient.close

**Source file:** `src/languages/erlang-py/close.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If self._proc was None on entry, the method returns immediately with no observable side effects
  - If self._proc was a running process, it is no longer executing after the method returns
  - The subprocess is first asked to shut down gracefully; if it does not exit within a bounded interval, it is forcibly terminated; if it still does not exit after a second bounded interval, it is forcibly killed
  - All I/O streams connected to the subprocess (stdin and stdout) are closed before the method returns, regardless of whether individual shutdown or stream-close operations succeed or fail
  - self._proc is set to None
  - No exception raised during any shutdown or cleanup step propagates to the caller

---

### Actual Behavior

self._proc is None. If the pre-call value of self._proc (denoted old(self._proc)) was a subprocess.Popen instance p, then p.stdin and p.stdout have been closed (or were already None). Additionally, if p was still running at the beginning of the method (p.poll() returned None), then p has been sent a shutdown request and an exit notification, and an attempt to wait for its termination was made; if the wait timed out, p.terminate() was called and another wait attempted; if that also timed out, p.kill() was called. No guarantees are made about whether p has fully terminated by the end of the method. These side effects are guaranteed even if an exception escapes the method, because they are performed in a finally block.

---

## Code Evidence

Line 18: proc.terminate()
Line 22: proc.kill()

---

## Trigger Condition

The specification requires that no exception raised during any shutdown or cleanup step propagates to the caller. The code catches exceptions from self.request, self.notify, the two proc.wait calls, and stream-close OSErrors, but it does not catch exceptions from proc.terminate() or proc.kill(). If either of those calls fails, the exception will leak out, violating the specification.

---

## How to trigger the bug

The `close()` method (in `src/languages/erlang.py`, lines 262-291) enters the shutdown path when `proc.poll()` returns `None`. After `proc.wait(timeout=5)` raises `subprocess.TimeoutExpired`, it calls `proc.terminate()` without any exception guard. If `proc.terminate()` raises (e.g., `OSError` because the subprocess no longer exists), the exception propagates to the caller.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self._proc` | A mock `subprocess.Popen` whose `poll()` returns `None` and whose `terminate()` raises `OSError("No such process")` |
| `self.request` / `self.notify` | Mocked to raise immediately (bypassed via `except Exception: pass`) |
| `proc.wait()` | Mocked to raise `subprocess.TimeoutExpired` |

### Expected (spec-correct) Output

`None` — the method should catch all exceptions during shutdown and return normally.

### Actual (buggy) Output

`OSError("No such process")` raised from `proc.terminate()` — the exception propagates to the caller, violating the specification.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import subprocess
from unittest.mock import Mock

sys.path.insert(0, ".")
from src.languages.erlang import ElpClient

client = ElpClient.__new__(ElpClient)
client._proc = Mock(spec=subprocess.Popen)
client._proc.stdin = Mock()
client._proc.stdout = Mock()
client._proc.poll.return_value = None
client._proc.wait = Mock(side_effect=subprocess.TimeoutExpired(cmd=["mock"], timeout=5))
client._proc.terminate = Mock(side_effect=OSError("No such process"))
client.request = Mock(side_effect=Exception("bypass"))
client.notify = Mock(side_effect=Exception("bypass"))

client.close()  # raises OSError("No such process")
# actual (buggy) output: OSError: No such process
# expected (correct) output: None (no exception)
```

---

## Probe Script

```python
"""Probe script for bug: proc.terminate()/proc.kill() not exception-guarded in ElpClient.close()."""
import sys
import subprocess
from unittest.mock import Mock

sys.path.insert(0, ".")
from src.languages.erlang import ElpClient

# Create a bare ElpClient without actually starting an ELP subprocess.
# We only need the instance so we can call close().
client = ElpClient.__new__(ElpClient)

# Mount a mock subprocess.Popen that simulates a still-running process.
proc = Mock(spec=subprocess.Popen)
proc.stdin = Mock()
proc.stdout = Mock()
proc.poll.return_value = None          # process is still running → enter shutdown branch

# Make wait() raise TimeoutExpired so we reach the terminate() call.
proc.wait = Mock(side_effect=subprocess.TimeoutExpired(cmd=["mock"], timeout=5))

# The bug: terminate() raises because it's not wrapped in try/except.
proc.terminate = Mock(side_effect=OSError("No such process"))

client._proc = proc

# request() and notify() are patched so they raise immediately (caught by the
# existing except Exception: pass guards), avoiding a real LSP handshake.
client.request = Mock(side_effect=Exception("mock — bypass LSP"))
client.notify = Mock(side_effect=Exception("mock — bypass LSP"))

# Also ensure _write_lock exists (used by _send, which is called by notify
# via the patched methods — but request/notify are fully mocked so this is
# a safeguard).
import threading
client._write_lock = threading.Lock()

expected = "OSError"   # spec says no exception should propagate
passed = False

try:
    client.close()
    # If we reach here, no exception propagated — bug NOT confirmed.
    print("NOT CONFIRMED — close() completed without raising")
except OSError as exc:
    passed = True
    print(f"CONFIRMED — close() raised OSError: {exc}")
except Exception as exc:
    passed = True
    print(f"CONFIRMED — close() raised {type(exc).__name__}: {exc}")

# Also verify that the finally block still ran (proc set to None).
if passed and client._proc is None:
    pass  # correct - finally block ran despite the exception
elif passed:
    print("WARNING: finally block did not set _proc to None")
```

### Probe Output

```
CONFIRMED — close() raised OSError: No such process
```
