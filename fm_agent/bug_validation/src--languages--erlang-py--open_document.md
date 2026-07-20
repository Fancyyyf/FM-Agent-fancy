# Bug Report: ElpClient.open_document

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/open_document.py` (actual source: `src/languages/erlang.py`)
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Sends a `textDocument/didOpen` LSP notification to the backend for the
    document at the absolute, resolved path derived from path
  - The notification URI is the `file://` URI of the resolved path
  - When source is a non-None string, the notification carries source as the
    document text
  - When source is None, the notification carries the file contents at the
    resolved path as the document text
  - The document is registered with language identifier "erlang" and version 1
  - Returns None upon successful notification delivery
  - Raises an exception when source is None and the file at the resolved path
    cannot be read, or when the LSP communication channel is not open

---

### Actual Behavior

The code block finishes execution either normally or by raising an exception. If it finishes normally, a 'textDocument/didOpen' notification has been sent to the LSP backend with parameters: 'textDocument.uri' = Path(path).resolve().as_uri(), 'textDocument.languageId' = 'erlang', 'textDocument.version' = 1, 'textDocument.text' = (source if source is not None else the text content read from the resolved file using UTF-8 encoding and 'replace' error handling). The self object remains an ElpClient instance with the open communication channel. If an exception is raised, no notification was sent; the exception originates from either the path resolution (Path(path).resolve()) or, when source is None, the file read operation (document.read_text(...)). Formally, letting R = Path(path).resolve(), T = source if source is not None else (if file read succeeds then read_text(R) else ), and ok denote no exception raised: (ok  sent(self, \"textDocument/didOpen\", {\"textDocument\": {\"uri\": R.as_uri(), \"languageId\": \"erlang\", \"version\": 1, \"text\": T}}))  (ok  sent(self, \"textDocument/didOpen\", _)  (source is None  (file_read_error  path_resolution_error))).

---

## Code Evidence

Line 5: self.notify(...) is executed without any check on the communication channel state, failing to raise the required exception.

---

## Trigger Condition

The specification requires an exception when the LSP communication channel is not open, but the code invokes self.notify (Line 5) without verifying the channel state. If self.notify does not raise an exception itself (its contract does not mandate one), the function returns None instead of raising, violating the specification.

---

## How to trigger the bug

The trigger condition describes a scenario where `open_document` is called while the LSP communication channel is not open. In the actual code, `self.notify()` calls `self._send()`, which contains a guard:

```python
def _send(self, message: dict):
    if self._proc is None or self._proc.stdin is None:
        raise RuntimeError("ELP client is not running")
```

This guard checks whether `self._proc` (the ELP subprocess) is `None` or its `stdin` is `None`. When the channel is not open (client not started, process dead, etc.), `_send` raises a `RuntimeError`, which propagates through `notify()` → `open_document()`. The specification requirement — "Raises an exception when the LSP communication channel is not open" — is therefore satisfied by the indirect check in `_send`.

The logic verification step appears to have missed that `self.notify()` does not itself perform the check but delegates to `self._send()`, which performs it reliably.

### Inputs

| Parameter | Value |
|-----------|-------|
| `path` | Path to a valid `.erl` file (temp file) |
| `source` | `None` (forces file read) |

### Expected (spec-correct) Output

An exception should be raised (e.g., `RuntimeError` or similar).

### Actual (buggy) Output

`RuntimeError("ELP client is not running")` is raised — matching the spec.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
import tempfile
from src.languages.erlang import ElpClient

# Create client without starting (no __enter__ → _proc is None)
client = ElpClient(proj_dir="/tmp")

with tempfile.NamedTemporaryFile(mode="w", suffix=".erl", delete=False) as f:
    f.write("-module(test).\n-export([hello/0]).\nhello() -> ok.\n")
    tmp_path = f.name

try:
    client.open_document(tmp_path, source=None)
    # actual (buggy) output: <would return None — but this is unreachable>
    # expected (correct) output: <exception raised>
except RuntimeError as e:
    print(f"Exception raised as expected: {e}")
```

---

## Probe Script

```python
"""Probe script for bug src--languages--erlang-py--open_document.

Spec claim: open_document must raise an exception when the LSP communication
channel is not open.
Bug claim: The code calls self.notify() without checking channel state, so it
may return None instead of raising.
"""
import tempfile
from pathlib import Path
from src.languages.erlang import ElpClient


def main():
    # Create an ElpClient WITHOUT entering the context manager.
    # This leaves _proc = None, meaning the LSP channel is not open.
    client = ElpClient(proj_dir="/tmp")

    # Create a valid temp file so path resolution and file reading succeed.
    # Only the channel-not-open check (inside _send) should trigger.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".erl", delete=False) as f:
        f.write("-module(test).\n-export([hello/0]).\nhello() -> ok.\n")
        tmp_path = f.name

    try:
        # source=None forces file reading; the file exists so that step passes.
        # The buggy path is: path resolution OK, file read OK, then self.notify()
        # is called while _proc is None. According to the spec, this MUST raise.
        result = client.open_document(tmp_path, source=None)
        # If we get here, the function returned normally (returned None implicitly).
        # Per the spec this is a violation — an exception should have been raised.
        print(
            "CONFIRMED "
            f"— open_document with no channel returned {result!r} instead of raising"
        )
    except Exception as exc:
        # An exception was raised, which satisfies the specification.
        # The function correctly raised when the channel was not open.
        print(
            f"NOT CONFIRMED "
            f"— open_document with no channel correctly raised {type(exc).__name__}: {exc}"
        )
    finally:
        # Clean up the temp file.
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — open_document with no channel correctly raised RuntimeError: ELP client is not running
```
