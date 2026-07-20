# Bug Report: _copy_opencode_output

**Source file:** `src/opencode_trace-py/_copy_opencode_output.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- All data from stream has been consumed: read(4096) has been called
    repeatedly until an empty string signals EOF
  - stream.close() has been called — the stream resource is released
  - If trace_log_path was truthy, a file at that path exists and contains the
    complete data read from the stream, encoded in UTF-8 with replacement
    characters for unencodable data; each chunk is flushed individually
  - If trace_log_path was falsy, no file is created or written
  - The trace log file (if opened) is closed before the stream is closed
  - Regardless of exceptions during reading or writing, both the trace log
    file (if opened) and the stream are guaranteed to be closed

---

### Actual Behavior

After the function _copy_opencode_output runs, the following post-conditions hold given the pre-conditions. Let S be `stream`, P be `trace_log_path` (original argument), and T be the local variable `trace_log`.

**Normal termination (no exception):**
- The function returns `None`.
- All data from S has been read until EOF (the loop terminated on an empty string).
- If P was truthy: a file at P was opened for text writing with UTF-8 encoding and `errors='replace'`; every chunk read from S was written to that file and flushed; the file is closed (T.close() called).
- S is closed (S.close() called).

**Exceptional termination (exception raised during try block or while opening P):**
- The exception propagates out of the function.
- If T was successfully opened (i.e., P truthy and `open(P)` succeeded without exception), then T is closed (the `finally` block ensures T.close() executes).
- S remains open because S.close() is never reached.
- If P was falsy, T remains `None` and no file operations occur.
- The file at P (if opened) may contain a partial copy of the data read before the exception occurred.

**Additional note:** If an exception occurs during S.close() itself, S may be left open, but given the specification that S.close() always succeeds (only raising ValueError if already closed), this path is considered unreachable under the pre-condition.

---

## Code Evidence

Line 15: stream.close()

In the extracted function file (line 73), the code structure is:

```python
def _copy_opencode_output(stream, trace_log_path=None):
    trace_log = None
    try:
        if trace_log_path:
            trace_log = open(trace_log_path, "w", encoding="utf-8", errors="replace")
        for chunk in iter(lambda: stream.read(4096), ""):
            if not chunk:
                break
            if trace_log:
                trace_log.write(chunk)
                trace_log.flush()
    finally:
        if trace_log:
            trace_log.close()
    stream.close()       # <-- BUG: outside finally block
```

---

## Trigger Condition

Specification requires that regardless of exceptions, the stream is guaranteed to be closed. However, `stream.close()` (line 73 in the extracted function) is not inside a finally block, so if an exception occurs during the try block (e.g., during `stream.read()` or `trace_log.write()`), the exception propagates after the finally block closes `trace_log`, but `stream.close()` is never executed, leaving the stream open.

---

## How to trigger the bug

Create a stream whose `read()` method raises an exception. When `_copy_opencode_output` is called with this stream, the exception occurs during the `for` loop iteration. The `finally` block runs and closes `trace_log` (if opened), but then the exception propagates past `stream.close()`, leaving the stream open.

### Inputs

| Parameter | Value |
|-----------|-------|
| `stream` | FaultyStream object whose `read()` raises `OSError` |
| `trace_log_path` | `None` (or any valid path) |

### Expected (spec-correct) Output

The stream MUST be closed regardless of exceptions. After calling `_copy_opencode_output`, `stream.closed` should be `True`.

### Actual (buggy) Output

After calling `_copy_opencode_output` with a faulty stream, the `OSError` propagates out, but `stream.closed` remains `False` — the stream was never closed.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import importlib.util
import os

module_path = "fm_agent/extracted_functions/src/opencode_trace-py/_copy_opencode_output.py"
spec = importlib.util.spec_from_file_location("_copy_opencode_output", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FaultyStream:
    def read(self, n):
        raise OSError("simulated read error")
    def close(self):
        self.closed = True

s = FaultyStream()
s.closed = False
try:
    mod._copy_opencode_output(s)
except OSError:
    pass

print(s.closed)  # actual (buggy) output: False
# expected (correct) output: True
```

---

## Probe Script

```python
"""Probe script: verify that stream.close() is skipped when exception occurs during read."""

import sys
import os
import importlib.util
import tempfile

# Load the extracted function module via importlib (no __init__.py in tree)
module_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "extracted_functions",
    "src",
    "opencode_trace-py",
    "_copy_opencode_output.py",
)
spec = importlib.util.spec_from_file_location("_copy_opencode_output", module_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_copy_opencode_output = mod._copy_opencode_output


class FaultyStream:
    """A readable stream that raises OSError after returning some data."""

    def __init__(self):
        self.closed = False

    def read(self, _n):
        raise OSError("simulated stream read error after some data")

    def close(self):
        self.closed = True


def run_test(desc, trace_log_path):
    stream = FaultyStream()
    exception_caught = False
    try:
        _copy_opencode_output(stream, trace_log_path=trace_log_path)
    except OSError:
        exception_caught = True
    except Exception as e:
        print(f"ERROR: unexpected exception type in {desc}: {type(e).__name__}: {e}")
        return False, False

    if not exception_caught:
        print(f"ERROR: expected OSError was not raised in {desc}")
        return False, False

    return exception_caught, stream.closed


# Test 1: trace_log_path=None (no file opened)
exception_raised_1, stream_closed_1 = run_test("no trace log", trace_log_path=None)

# Test 2: trace_log_path set (file opened, write happens or fails)
tmp_path = os.path.join(tempfile.gettempdir(), f"probe_test_{os.getpid()}.log")
exception_raised_2, stream_closed_2 = None, None
try:
    exception_raised_2, stream_closed_2 = run_test("with trace log", trace_log_path=tmp_path)
finally:
    # Clean up
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

# Both tests should show: exception raised but stream NOT closed (bug)
stream_leaked = (exception_raised_1 and not stream_closed_1)

if exception_raised_1 is None or exception_raised_2 is None:
    print("ERROR: tests did not complete")
    sys.exit(1)

if stream_leaked:
    print(
        "CONFIRMED — exception raised but stream.close() was NOT called "
        "(stayed open). The spec requires stream is guaranteed closed regardless "
        "of exceptions, but stream.close() is outside the finally block."
    )
else:
    print(
        "NOT CONFIRMED — stream was closed despite the exception, "
        "or the expected OSError was not raised."
    )
```

### Probe Output

```
CONFIRMED — exception raised but stream.close() was NOT called (stayed open). The spec requires stream is guaranteed closed regardless of exceptions, but stream.close() is outside the finally block.
```
