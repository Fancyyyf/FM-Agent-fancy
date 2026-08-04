# Bug Report: ElpClient::_send

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/erlang-py/ElpClient::_send.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the server process is not running or its stdin stream is not writable, raises RuntimeError. Otherwise: message is serialized to a UTF-8 JSON byte sequence with minimal separators (commas and colons without whitespace) and without ASCII-escaping non-ASCII characters; the serialized byte sequence is prepended with an LSP Content-Length header (Content-Length: <octet_count>\r\n\r\n) to form a complete frame; the complete frame is written to the server process's stdin under exclusive acquisition of the write lock and the stream is flushed, ensuring the frame is delivered to the server as a single atomic unit. Returns None after successful transmission. Raises an OSError (or subclass, such as BrokenPipeError) when the stdin write or flush operation fails.

---

### Actual Behavior

If the function raises no exception, then self._proc and self._proc.stdin are not None, and the JSON-RPC frame constructed from `message` (UTF-8 encoded JSON with ensured non-ASCII and compact separators) has been written and flushed to the server's stdin within the `with self._write_lock` block, so the lock is now released. The frame content exactly is `Content-Length: <payload_length>\r\n\r\n<payload_utf8>`. The message argument remains unchanged. If the function raises `RuntimeError`, then `self._proc is None or self._proc.stdin is None` is true, no frame is written, the lock is unaffected, and the server stdin is unmodified. Formal logic: (Exception  (self._proc  None  self._proc.stdin  None)  sent(frame)  lock_released(self._write_lock))  (Exception(RuntimeError)  (self._proc = None  self._proc.stdin = None)  sent(frame)  lock_unacquired(self._write_lock)  stdin_unchanged(self._proc.stdin)).

---

## Code Evidence

Line 2:         if self._proc is None or self._proc.stdin is None:

---

## Trigger Condition

The specification requires raising RuntimeError when the server process is not running or its stdin stream is not writable. The code only checks for None values, missing cases where the process has exited but the Popen object and stdin still exist. In such a case, the code raises an OSError instead of RuntimeError, violating the contract.

---

## How to trigger the bug

When the ELP server process terminates unexpectedly (crashes, is killed externally, etc.), the `self._proc` Popen object and its `stdin` pipe remain as non-None objects. Since `_send` only checks `is None`, the guard passes. The code then attempts to write the LSP frame to the dead process's stdin, which raises `BrokenPipeError` (a subclass of `OSError`). The specification requires `RuntimeError` in this scenario because the server process is not running.

### Inputs

| Parameter | Value |
|-----------|-------|
| `message` | `{"jsonrpc": "2.0", "method": "test/method", "params": {"key": "value"}}` |
| `self._proc` | A `MagicMock` where `poll()` returns `0` (process exited) and `stdin.write()` raises `BrokenPipeError` |
| `self._proc.stdin` | A `MagicMock` (not None) |

### Expected (spec-correct) Output

`RuntimeError` raised (server process is not running)

### Actual (buggy) Output

`BrokenPipeError` raised (write to dead pipe fails at the OS level, bypassing the None check)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import MagicMock
from src.languages.erlang import ElpClient

client = object.__new__(ElpClient)
client._write_lock = MagicMock()

mock_proc = MagicMock()
mock_proc.poll.return_value = 0          # Process has exited
mock_proc.stdin = MagicMock()
mock_proc.stdin.write.side_effect = BrokenPipeError

client._proc = mock_proc

# Call via public API: notify() exercises _send()
try:
    client.notify("test/method", {"key": "value"})
except BrokenPipeError:
    print("Bug: BrokenPipeError raised instead of RuntimeError")
except RuntimeError:
    print("Correct: RuntimeError raised as spec requires")
# actual (buggy) output: BrokenPipeError
# expected (correct) output: RuntimeError
```

---

## Probe Script

```python
"""Probe script for bug: src--languages--erlang-py--ElpClient::_send

Bug: ElpClient._send() raises OSError (BrokenPipeError) instead of RuntimeError
when the server process has exited but self._proc is not None. The spec requires
RuntimeError when the server process is not running; the code only checks for
None values, not whether the process is alive via poll().
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure the repo root is on sys.path so 'src.languages.erlang' is importable.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.languages.erlang import ElpClient


try:
    # ------------------------------------------------------------------
    # Build a mock ElpClient that bypasses real __init__ (no subprocess).
    # Set up self._proc: not None, stdin not None, but poll() shows exited.
    # This simulates: the ELP server process terminates unexpectedly, but
    # the Popen object and its stdin pipe still exist.
    # ------------------------------------------------------------------
    client = object.__new__(ElpClient)
    client._write_lock = MagicMock()

    mock_proc = MagicMock()
    mock_proc.poll.return_value = 0          # Process has exited (return code 0)
    mock_proc.stdin = MagicMock()
    # Writing to a dead process's stdin raises BrokenPipeError on Linux
    mock_proc.stdin.write.side_effect = BrokenPipeError

    client._proc = mock_proc

    # ------------------------------------------------------------------
    # Exercise _send through the public API: notify().
    # ------------------------------------------------------------------
    actual_type = None
    try:
        client.notify("test/method", {"key": "value"})
    except RuntimeError:
        actual_type = RuntimeError
    except BrokenPipeError:
        actual_type = BrokenPipeError
    except OSError:
        actual_type = OSError
    except Exception as e:
        actual_type = type(e)

    # Spec says: "If the server process is not running or its stdin stream
    # is not writable, raises RuntimeError."
    # The code only checks for None, so it proceeds to write and gets
    # BrokenPipeError (a subclass of OSError) instead of RuntimeError.
    expected_type = RuntimeError
    bug_reproduced = actual_type != expected_type

    if bug_reproduced:
        print(
            f"CONFIRMED — actual: {actual_type.__name__} raised "
            f"| expected: RuntimeError | process exited (poll()=0) but "
            f"self._proc is not None, so None check passes; write to dead "
            f"pipe raises {actual_type.__name__} instead of RuntimeError"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual_type.__name__}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: BrokenPipeError raised | expected: RuntimeError | process exited (poll()=0) but self._proc is not None, so None check passes; write to dead pipe raises BrokenPipeError instead of RuntimeError
```
