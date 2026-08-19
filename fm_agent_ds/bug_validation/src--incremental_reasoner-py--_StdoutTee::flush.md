# Bug Report: _StdoutTee::flush

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

All buffered data written to the console stream is flushed to the underlying device. All buffered data written to the log stream is flushed to the underlying file, unless the log stream is closed, in which case no flush is attempted and no exception is raised. Returns None.

---

### Actual Behavior

If the method returns normally (no exception raised), then all buffered data in the console stream has been committed to the underlying device, and if the log stream was not closed at the time of the call, all buffered data in the log stream has been committed to the underlying file. If an exception is raised during the execution of either flush() call, the method does not complete normally, and the state of the stream buffers is unspecified: the console flush may have partially succeeded or not started, and the log flush may not have been called. Formal logic: For normal termination: (flush_call_console(succeed)  ( log_stream_not_closed_at_call_time  flush_call_log(succeed) ) ). For abnormal termination: raised(exception)  {FlushError, IOError, ...}.

---

## Code Evidence

Line 2: self._console.flush()

---

## Trigger Condition

The specification requires that after the call, all buffered data in the log stream is flushed (unless the log stream is closed). The code does not flush the log stream when the console flush raises an exception, violating that post-condition.

---

## How to trigger the bug

When `_StdoutTee.flush()` is called and `self._console.flush()` raises an exception (e.g. `IOError`), execution never reaches the log stream flush on line 96-97. The exception propagates out, and `self._log_stream.flush()` is never called, violating the spec's post-condition that all buffered data in the log stream must be flushed unless the log stream is closed.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self._console` | A mock stream whose `flush()` raises `IOError` |
| `self._log_stream` | A mock stream with `closed = False` |

### Expected (spec-correct) Output

The log stream's `flush()` is called (unless the log stream is closed), regardless of whether the console flush succeeds or fails.

### Actual (buggy) Output

An exception propagates from `self._console.flush()` and the log stream's `flush()` is never called.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _StdoutTee

class RaisingConsole:
    def write(self, data): pass
    def flush(self): raise IOError("fail")

class TrackingLog:
    def __init__(self):
        self.closed = False
        self.flush_called = False
    def write(self, data): pass
    def flush(self): self.flush_called = True

tee = _StdoutTee(RaisingConsole(), TrackingLog())
try:
    tee.flush()
except IOError:
    pass

# actual (buggy) output: TrackingLog.flush_called is False
# expected (correct) output: TrackingLog.flush_called is True
```

---

## Probe Script

```python
"""Probe script for bug: _StdoutTee::flush — log stream not flushed when console flush raises."""

import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'config' and 'src' are both importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Create an isolated temp directory for any probe-owned file I/O
# (even though this test is pure in-memory, the guard requires it).
_probe_tmp = tempfile.mkdtemp(prefix="probe_StdoutTee_flush_")


# ---------------------------------------------------------------------------
# Mock objects
# ---------------------------------------------------------------------------
class RaisingConsole:
    """A console stream whose flush() deliberately raises IOError."""

    def write(self, data):
        pass

    def flush(self):
        raise IOError("Simulated console flush failure")


class TrackingLogStream:
    """A log stream that records whether flush() was called."""

    def __init__(self):
        self.closed = False
        self.flush_called = False

    def write(self, data):
        pass

    def flush(self):
        self.flush_called = True


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------
def main():
    try:
        from src.incremental_reasoner import _StdoutTee
    except ImportError as e:
        print(f"ERROR: Could not import _StdoutTee: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during import of _StdoutTee: {e}")
        sys.exit(1)

    console = RaisingConsole()
    log_stream = TrackingLogStream()
    tee = _StdoutTee(console, log_stream)

    exception_raised = False
    try:
        tee.flush()
    except IOError:
        exception_raised = True
    except Exception as e:
        print(f"ERROR: Unexpected exception type from flush(): {type(e).__name__}: {e}")
        sys.exit(1)

    if exception_raised and not log_stream.flush_called:
        print(
            "CONFIRMED — exception propagated from console flush, "
            "but log stream flush was never called (spec requires it)"
        )
    elif exception_raised and log_stream.flush_called:
        print(
            "NOT CONFIRMED — exception propagated, "
            "but log stream was flushed before the exception (spec satisfied)"
        )
    elif not exception_raised:
        if log_stream.flush_called:
            print(
                "NOT CONFIRMED — flush() returned normally and "
                "log stream was flushed (exception was handled gracefully)"
            )
        else:
            print(
                "NOT CONFIRMED — flush() returned normally but "
                "log stream was not flushed (unexpected behavior)"
            )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — exception propagated from console flush, but log stream flush was never called (spec requires it)
```
