# Bug Report: _copy_opencode_output

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/opencode_trace-py/_copy_opencode_output.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

stream is closed; if trace_log_path is not None, a file exists at trace_log_path containing the concatenation of every byte read from stream before exhaustion, the file is closed, and its content is UTF-8 encoded with unencodable characters replaced; if trace_log_path is None, no file is created; stream is closed and (if opened) the trace log file is closed under all execution paths, including when an exception is raised during reading or writing

---

### Actual Behavior

After the function completes (whether normally or via an unhandled exception), the following holds: (1) The `stream` object is closed. (2) If `trace_log_path` was not `None` and the attempt to open the file succeeded, then a file at `trace_log_path` exists, is closed, and its content equals the concatenation of a finite prefix of the strings returned by `stream.read(4096)`  specifically, all chunks successfully read before the stream was exhausted or an error occurred. (3) If `trace_log_path` was not `None` but the file could not be opened (the `open()` call raised an exception), then the file at that path remains unchanged and no content was written. (4) If `trace_log_path` was `None`, no file was opened or written. Formally:

stream.closed = True  
( (trace_log_path  None)  
    ( (  prefix P of stream_chunks : file_content(trace_log_path) = concat(P)    file_closed(trace_log_path) )
        ( file_unchanged(trace_log_path)   opened(trace_log_path) )
    )
)

where `stream_chunks` is the sequence of strings obtained by repeatedly calling `stream.read(4096)` until exhaustion or an exception.

---

## Code Evidence

Line 10: trace_log.write(chunk)

---

## Trigger Condition

When the stream is a binary stream, stream.read(4096) returns bytes (e.g., b'\xff'). At line 10, the code attempts to write these bytes directly to a text file opened with encoding='utf-8'. This raises TypeError because write() expects a string, not bytes. The specification requires that every byte read from the stream be written to the file as UTF-8 encoded text with unencodable characters replaced (i.e., decoding the bytes with 'replace' and encoding to UTF-8). The code does not perform this conversion, causing it to fail to produce the required file content and instead raise an exception.

---

## How to trigger the bug

When `_copy_opencode_output` is called with a binary stream (e.g., `io.BytesIO`), the `stream.read(4096)` call returns `bytes` objects instead of `str`. The trace log file is opened in text mode (`open(trace_log_path, "w", encoding="utf-8", errors="replace")`), so `trace_log.write(bytes)` raises `TypeError: write() argument must be str, not bytes`. The specification requires that every byte be written as UTF-8 text with unencodable characters replaced, but the code never decodes the bytes before writing them.

### Inputs

| Parameter | Value |
|-----------|-------|
| `stream` | `io.BytesIO(b"hello\\xff\\x00world")` — a binary stream containing bytes that are not all valid UTF-8 |
| `trace_log_path` | A path to a new temporary file |

### Expected (spec-correct) Output

The function should complete without error. The trace log file at `trace_log_path` should contain the UTF-8 decoded text with unencodable bytes (such as `\xff`) replaced by the Unicode replacement character `\ufffd`. Expected file content: `"hello\ufffd\0world"`.

### Actual (buggy) Output

`TypeError: write() argument must be str, not bytes` is raised when `trace_log.write(b"hello\xff\x00world")` is called at line 10. The file is closed via the `finally` block, but no valid content was written.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import io
import sys
import tempfile, os

_REPO_ROOT = "/home/fancy/Projects_Vault/FM-Agent"
sys.path.insert(0, _REPO_ROOT)
from src.opencode_trace import _copy_opencode_output

binary_stream = io.BytesIO(b"hello\xff\x00world")
tmp_dir = tempfile.mkdtemp()
trace_log_path = os.path.join(tmp_dir, "trace.log")

try:
    _copy_opencode_output(binary_stream, trace_log_path)
except TypeError as e:
    print(f"TypeError: {e}")
# actual (buggy) output: TypeError: write() argument must be str, not bytes
# expected (correct) output: no exception; file contains decoded text with replacement characters
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe for _copy_opencode_output: TypeError when stream delivers bytes to a text-mode trace_log.

Spec claim: Every byte read from stream is written to the trace log file as UTF-8
encoded text with unencodable characters replaced.

Actual behavior: When the stream returns bytes (binary stream), line 10
(trace_log.write(chunk)) raises TypeError because the trace_log file is opened in
text mode and write() expects str, not bytes.
"""
import io
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

try:
    from src.opencode_trace import _copy_opencode_output

    # Create a temporary directory for the trace log output
    tmp_dir = tempfile.mkdtemp(prefix="probe_copy_opencode_")
    trace_log_path = os.path.join(tmp_dir, "trace.log")

    # Create a binary stream containing data that will trigger the bug.
    # The byte b'\xff' is not valid UTF-8; per the spec it should be replaced
    # with the Unicode replacement character U+FFFD.
    binary_data = b"hello\xff\x00world"
    binary_stream = io.BytesIO(binary_data)

    type_error_raised = False
    actual_error = None

    try:
        _copy_opencode_output(binary_stream, trace_log_path)
    except TypeError as e:
        type_error_raised = True
        actual_error = str(e)
    except Exception as e:
        actual_error = f"{type(e).__name__}: {e}"
    else:
        # Function completed without error -- this would be NOT CONFIRMED
        pass

    # Verify the stream was closed (spec requires this)
    stream_was_closed = binary_stream.closed

    # The bug is confirmed if:
    # 1. TypeError was raised when trying to write bytes to a text file
    passed = type_error_raised

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(
        f"CONFIRMED — TypeError raised when writing bytes to text-mode trace log: "
        f"{actual_error}"
    )
else:
    if actual_error:
        print(f"NOT CONFIRMED — unexpected exception: {actual_error}")
    else:
        print("NOT CONFIRMED — function completed without error for binary stream")
```

### Probe Output

```
CONFIRMED — TypeError raised when writing bytes to text-mode trace log: write() argument must be str, not bytes
```
