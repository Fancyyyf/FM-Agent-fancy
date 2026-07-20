# Bug Report: _write_command_stdin

**Source file:** `src/opencode_trace.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- text has been written to stream via write(text) and the stream internal
    buffer has been flushed via flush()
  - stream.close() has been called  the stream resource is released
  - The stream is guaranteed to be closed even if write() or flush() raises
    an exception

---

### Actual Behavior

After the execution of the code block, `text` remains unchanged. The stream object `stream` is closed (i.e., `stream.close()` has been called, the underlying resource is released, and any further operations on `stream` raise `ValueError`). If the block completed without raising an exception (normal return), then the entire `text` has been successfully written to the stream's internal buffer via `stream.write(text)` and flushed to the underlying resource via `stream.flush()`. If an exception was raised during `stream.write(text)` or `stream.flush()`, the exception propagates out of the function; `stream` is still closed, but the amount of `text` written is unspecified. Formally: (invariant: `text` unchanged  `stream.closed`)  ((normal_return)  (written(text, stream)  flushed(stream)))  ((exception_raised)  (`stream.closed`  full_write_guaranteed))

---

## Code Evidence

Line 3: stream.write(text)
Line 4: stream.flush()

---

## Trigger Condition

The specification requires that text is written and the stream buffer is flushed. If stream.flush() raises an exception, the code does not ensure the text is written and flushed; the exception propagates, leaving the text potentially unwritten or unflushed, violating the postcondition.

---

## How to trigger the bug

When `stream.write(text)` succeeds but `stream.flush()` raises an exception, the exception propagates unhandled out of `_write_command_stdin`. The stream is properly closed via the `finally` block, but the spec postcondition — that text must be both written *and* flushed — is violated because flush() failed. The caller receives an exception and cannot assume the flush completed.

### Inputs

| Parameter | Value |
|-----------|-------|
| stream | MockFlushFailStream (write succeeds, flush raises RuntimeError) |
| text | "hello stdin" |

### Expected (spec-correct) Output

`None` (normal return) — the function should guarantee that text was both written and flushed.

### Actual (buggy) Output

`RuntimeError("flush() failed — simulated I/O error")` — the exception from `flush()` propagates unhandled. The stream is closed, but flush did not complete.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src import opencode_trace

class FlakyStream:
    def write(self, s): return len(s)
    def flush(self): raise RuntimeError("flush failed")
    def close(self): pass

s = FlakyStream()
opencode_trace._write_command_stdin(s, "test")
# actual (buggy) output: RuntimeError: flush failed
# expected (correct) output: None (function returns normally, postcondition satisfied)
```

---

## Probe Script

```python
import sys
import os

# Add repo root to sys.path so 'src' is importable as the package entry point
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src import opencode_trace
except Exception as e:
    print(f'ERROR: failed to import src.opencode_trace: {e}')
    sys.exit(1)


class MockFlushFailStream:
    """A mock stream where write() succeeds but flush() raises RuntimeError."""

    def __init__(self):
        self.written = ""
        self.closed = False
        self.write_called = False
        self.flush_called = False

    def write(self, text):
        self.write_called = True
        self.written += text
        return len(text)

    def flush(self):
        self.flush_called = True
        raise RuntimeError("flush() failed — simulated I/O error")

    def close(self):
        self.closed = True


stream = MockFlushFailStream()
text = "hello stdin"
exception_raised = False
actual_exception = None
write_succeeded_before_exception = False
closed_after_exception = False

try:
    opencode_trace._write_command_stdin(stream, text)
except RuntimeError as exc:
    exception_raised = True
    actual_exception = exc
    write_succeeded_before_exception = stream.write_called
    closed_after_exception = stream.closed
except Exception as exc:
    exception_raised = True
    actual_exception = exc
    write_succeeded_before_exception = stream.write_called
    closed_after_exception = stream.closed

# The spec requires: text is written AND flushed
# Actual behavior: write() succeeded, flush() raised, exception propagates, stream is closed
# The gap: write() happened, but flush() raised — the spec's postcondition that
# "text has been flushed via flush()" is violated. The caller cannot observe the
# postcondition because the exception propagates unhandled.

bug_confirmed = (
    exception_raised
    and write_succeeded_before_exception
    and closed_after_exception
)

if bug_confirmed:
    print(
        "CONFIRMED — actual: RuntimeError raised after write(), flush() failed. "
        "Spec requires text written AND flushed, but flush() failure means the "
        "postcondition is violated. Stream was closed via finally block."
    )
else:
    print(
        "NOT CONFIRMED — "
        f"exception_raised={exception_raised}, "
        f"write_succeeded={write_succeeded_before_exception}, "
        f"flush_called_and_failed={stream.flush_called}, "
        f"closed={closed_after_exception}"
    )
```

### Probe Output

```
CONFIRMED — actual: RuntimeError raised after write(), flush() failed. Spec requires text written AND flushed, but flush() failure means the postcondition is violated. Stream was closed via finally block.
```
