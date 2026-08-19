# Bug Report: _StdoutTee::write

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The string data is written to the console stream. The string data is written to the log stream unless the log stream is closed, in which case the log write is skipped and no exception is raised. Returns len(data), the number of characters in data.

---

### Actual Behavior

If the method returns normally, then data has been successfully written to self._console, and if self._log_stream was not closed before the write attempt, data has also been written to self._log_stream; the return value equals len(data). Formally:  s  State such that pre(s) and method terminates normally with value r, r = len(data)  written(s.self._console, data)  (s.self._log_stream.closed  written(s.self._log_stream, data)). If the method raises an exception (from either write call), the console and log stream may contain partial or no data, and no return value is produced.

---

## Code Evidence

Line 2: self._console.write(data)

---

## Trigger Condition

The specification requires that data is written to the console stream. The precondition states only that the console stream is open, not that it is open for writing. A valid input can provide an open console stream in read mode, causing self._console.write(data) to raise an exception. The code then does not write data to the console and does not return len(data), violating the specification.

---

## How to trigger the bug

When `_StdoutTee` is constructed with a `console` stream that is open but not writable (e.g., a file opened in read mode), calling `write()` raises `io.UnsupportedOperation: not writable` on `self._console.write(data)`. The specification requires this to succeed and return `len(data)`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `console` | A file stream opened in `'r'` (read-only) mode, e.g. `open('/tmp/tmpXXX', 'r')` |
| `log_stream` | A writable `io.StringIO()` instance |
| `data` | `"hello"` (5 characters) |

### Expected (spec-correct) Output

`5` (i.e., `len("hello")`)

### Actual (buggy) Output

`io.UnsupportedOperation: not writable` (exception raised at `self._console.write(data)`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import io
import os
import tempfile
from src.incremental_reasoner import _StdoutTee

fd, tmp_path = tempfile.mkstemp()
os.close(fd)
read_only_console = open(tmp_path, 'r')
log_stream = io.StringIO()

tee = _StdoutTee(read_only_console, log_stream)
tee.write("hello")
# actual (buggy) output: io.UnsupportedOperation: not writable
# expected (correct) output: 5
```

---

## Probe Script

```python
import sys
import io
import os
import tempfile
from pathlib import Path

# Ensure the repo root is on sys.path so 'src' can be imported.
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root))

try:
    from src.incremental_reasoner import _StdoutTee

    # Create a read-only file stream (open but not writable)
    fd, tmp_path = tempfile.mkstemp()
    os.close(fd)
    read_only_console = open(tmp_path, 'r')
    log_stream = io.StringIO()

    # /***** ACTUAL RESULT (what the code does) *****/
    tee = _StdoutTee(read_only_console, log_stream)
    actual = None
    bug_reproduced = False
    try:
        actual = tee.write("hello")
    except io.UnsupportedOperation as e:
        actual = f"UnsupportedOperation: {e}"
        bug_reproduced = True
    except Exception as e:
        actual = f"{type(e).__name__}: {e}"
        bug_reproduced = True

    # /***** EXPECTED RESULT (what the spec requires) *****/
    # Spec: "The string data is written to the console stream."
    #        "Returns len(data), the number of characters in data."
    # The spec does NOT say the console stream must be writable — only that it's open.
    expected = 5  # len("hello") = 5

    # Bug is confirmed if actual != expected (exception instead of returning len)
    passed = actual != expected

    read_only_console.close()
    os.unlink(tmp_path)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'UnsupportedOperation: not writable' | expected: 5
```
