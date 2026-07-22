# Bug Report: ElpClient._send

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- The JSON-serialized form of message is transmitted to the ELP
    subprocess's standard input using LSP transport protocol framing
  - The transmitted frame consists of a Content-Length header whose value
    is the length in bytes of the UTF-8 encoded JSON payload, followed by
    a CRLF blank line, then the UTF-8 encoded JSON payload itself
  - The header portion is ASCII-encoded; the payload is compact JSON with
    no whitespace between keys, values, colons, or commas, and all non-ASCII
    characters are preserved in their original form
  - Transmission is atomic with respect to other concurrent _send calls on
    the same client instance
  - On return, the complete frame has been delivered to the subprocess's
    input stream (the write has been flushed to the OS pipe)
  - Raises RuntimeError when the ELP subprocess is not running or its
    standard input is unavailable

---

### Actual Behavior

After execution under the given pre-condition, the method completes without raising an exception. The dict message is serialized to a JSON string (UTF-8 encoded), framed with a 'Content-Length' header, written atomically to self._proc.stdin under self._write_lock, and then flushed. The flush ensures all buffered data is pushed to the subprocess's console stream (unconditionally) and, if the log stream is open, to the log stream as well. After the method returns, self._proc.stdin remains open and writable, self._write_lock is released, and the entire frame has been successfully transmitted to the subprocess. Formally, let  be the pre-state and  the post-state. Then  satisfies: (1) The sequence of bytes written to the console stream of self._proc.stdin is .console_stream  frame, where frame = b'Content-Length: ' + len(payload_encoded).to_bytes() + b'\r\n\r\n' + payload_encoded and payload_encoded = json.dumps(message, ...).encode('utf-8'). (2) If the optional log stream associated with self._proc.stdin was open in , then its content is .log_stream  frame; otherwise it is unchanged. (3) The internal buffer of self._proc.stdin is empty. (4) self._write_lock is in the unlocked state. (5) self._proc.stdin remains non-None and writable.

---

## Code Evidence

Line 2:         if self._proc is None or self._proc.stdin is None:

---

## Trigger Condition

The specification requires raising RuntimeError when the subprocess's standard input is unavailable. The code only checks for None, but stdin can be unavailable while still being a non-None object (e.g., closed or broken pipe), causing a different exception to propagate instead of RuntimeError.

---

## How to trigger the bug

The `_send` method checks only whether `self._proc.stdin is None` on line 130 (`src/languages/erlang.py`). When `self._proc.stdin` is a non-None object whose underlying pipe is already closed (e.g., `close()` was called on the stream), the None check passes, but the subsequent `self._proc.stdin.write(frame)` call raises `ValueError("write to closed file")` instead of the `RuntimeError` required by the specification. The spec requires that **any** state where the subprocess's standard input is unavailable — not just `None` — triggers a `RuntimeError`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self._proc` | Non-None `MagicMock` object |
| `self._proc.stdin` | Non-None `MagicMock` with `closed=True` and `write()` raise `ValueError` |
| `message` (via `notify`) | `{'jsonrpc': '2.0', 'method': 'test/method', 'params': {'key': 'val'}}` |
| `self._write_lock` | `threading.Lock()` |

### Expected (spec-correct) Output

`RuntimeError` raised — because the standard input is unavailable (stdin is closed).

### Actual (buggy) Output

`ValueError("write to closed file")` raised — because the code only guards against `None`, not against an unavailable-but-non-None stream.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, threading
from unittest.mock import MagicMock
sys.path.insert(0, '.')
from src.languages.erlang import ElpClient

client = ElpClient('/tmp')

# Simulate stdin that is non-None but closed (unavailable)
mock_proc = MagicMock()
mock_stdin = MagicMock()
mock_stdin.closed = True
mock_stdin.write.side_effect = ValueError('write to closed file')
mock_stdin.flush.side_effect = ValueError('flush on closed file')
mock_proc.stdin = mock_stdin

client._proc = mock_proc
client._write_lock = threading.Lock()

# notify() → _send() — spec says RuntimeError, code gives ValueError
client.notify('test/method', {'key': 'val'})
# actual (buggy) output:  ValueError("write to closed file")
# expected (correct) output: RuntimeError
```

---

## Probe Script

```python
"""Probe for bug: ElpClient._send does not raise RuntimeError when stdin is unavailable."""

import sys
import threading
from unittest.mock import MagicMock

# Package entry-point import
sys.path.insert(0, '.')
from src.languages.erlang import ElpClient


def main():
    try:
        client = ElpClient('/tmp')

        # Simulate: self._proc is not None and self._proc.stdin is not None,
        # but stdin is closed/unavailable (e.g., pipe already closed).
        mock_proc = MagicMock()
        mock_stdin = MagicMock()
        mock_stdin.closed = True
        mock_stdin.write.side_effect = ValueError('write to closed file')
        mock_stdin.flush.side_effect = ValueError('flush on closed file')
        mock_proc.stdin = mock_stdin

        client._proc = mock_proc
        client._write_lock = threading.Lock()

        # Call a public method that internally uses _send
        client.notify('test/method', {'key': 'val'})

        # Spec requires RuntimeError; code reached here → bug NOT confirmed
        print('NOT CONFIRMED — no exception raised, but RuntimeError expected per spec')
    except RuntimeError:
        # RuntimeError IS raised → code matches spec → bug NOT confirmed
        print('NOT CONFIRMED — RuntimeError raised, which matches the spec')
    except Exception as exc:
        actual_type = type(exc).__name__
        expected = 'RuntimeError'

        if actual_type != expected:
            # Wrong exception type raised → bug CONFIRMED
            print(
                f'CONFIRMED — code raised {actual_type}("{exc}") '
                f'but spec requires {expected} when stdin is unavailable. '
                f'_proc.stdin is non-None (mock: {mock_stdin!r}) '
                f'yet stdin is closed/unavailable.'
            )
        else:
            print('NOT CONFIRMED — RuntimeError raised as expected')

if __name__ == '__main__':
    main()
```

### Probe Output

```
CONFIRMED — code raised ValueError("write to closed file") but spec requires RuntimeError when stdin is unavailable. _proc.stdin is non-None (mock: <MagicMock name='mock.stdin' id='138086028551440'>) yet stdin is closed/unavailable.
```
