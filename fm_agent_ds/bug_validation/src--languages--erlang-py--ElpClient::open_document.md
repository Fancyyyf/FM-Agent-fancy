# Bug Report: ElpClient::open_document

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The ELP server has been notified via an LSP 'textDocument/didOpen' notification that the text document at the resolved absolute path is open. When source is not None, the server has received the provided source text as the document content. When source is None, the server has received the on-disk file content read as UTF-8 with replacement characters substituted for any undecodable bytes. The opened document is registered with languageId 'erlang' and version 1. Raises an exception when the server is unreachable, the server rejects the notification, or the connection is lost.

---

### Actual Behavior

After the execution of the method `open_document`, one of the following holds: (1) No exception is raised; then the ELP server has received the `textDocument/didOpen` notification with `uri` equal to the file URI of the resolved absolute path of `path`, `languageId` set to `"erlang"`, `version` set to `1`, and `text` equal to the `source` argument if provided, otherwise the file content read using UTF-8 encoding with error replacement; and `self`'s connection to the ELP server remains active. (2) An exception is raised. If the exception is a file-read error (e.g., `FileNotFoundError`, `PermissionError`), then no `textDocument/didOpen` notification was sent and the connection remains active. If the exception originates from the `notify` call (due to server unreachable, connection loss, or notification rejection), then the notification was not delivered and the connection is no longer active. Formal post-condition: Let `normal_exit` be true if the block completed without an exception, `active` the predicate that self has an active ELP connection, `receive(N, params)` that the server received notification N with params, `file_exc` and `notify_exc` the respective exception conditions. Then (normal_exit → (receive(`"textDocument/didOpen"`, {uri: URI, languageId: "erlang", version: 1, text: text_val}) ∧ active)) ∧ (¬normal_exit → ((file_exc ∧ ¬receive(`"textDocument/didOpen"`, _) ∧ active) ∨ (notify_exc ∧ ¬receive(`"textDocument/didOpen"`, _) ∧ ¬active))).

---

## Code Evidence

Line 247: `source = document.read_text(encoding="utf-8", errors="replace")`

---

## Trigger Condition

When `source` is `None` (default), the code reads the file from disk using `Path.read_text()`. If the file at the given `path` does not exist, `read_text()` raises a `FileNotFoundError`. This is a file-read exception that propagates out of `open_document`, but the specification only allows exceptions when the server is unreachable, the server rejects the notification, or the connection is lost. File-read errors like `FileNotFoundError` are not included in the spec's allowed exception cases.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `path` | A string path to a non-existent file (e.g., `/tmp/probe/nonexistent_file.erl`) |
| `source` | `None` (default) |

### Expected (spec-correct) Output

Per the specification, exceptions are only allowed when:
- The server is unreachable
- The server rejects the notification
- The connection is lost

Since none of these conditions apply (no LSP connection is even attempted before `read_text()`), a `FileNotFoundError` should NOT be raised. The function should either handle the missing-file case gracefully (e.g., by treating it as empty content or raising a documented exception type) or the spec should be expanded to include file-read errors.

### Actual (buggy) Output

`FileNotFoundError: [Errno 2] No such file or directory: '/tmp/probe_open_document_.../nonexistent_file.erl'`

The error is raised at line 247 (`document.read_text(...)`) before any `textDocument/didOpen` notification is sent. The ELP server connection remains active (or uninitialized).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import ElpClient

client = ElpClient("/tmp/test_proj")
client.open_document("/tmp/nonexistent_file.erl")
# actual (buggy) output: FileNotFoundError: [Errno 2] No such file or directory
# expected (correct) output: No FileNotFoundError — only server/connection exceptions per spec
```

---

## Probe Script

```python
"""Probe for bug: ElpClient.open_document raises FileNotFoundError when source=None
and the file does not exist, but the spec only allows exceptions for
server unreachable, notification rejection, or connection loss.

Bug ID: src--languages--erlang-py--ElpClient::open_document

Expected (spec): Only server-reachable, notification-rejection, or
connection-loss exceptions are allowed. File-read errors like
FileNotFoundError should not propagate from open_document.

Actual (bug): document.read_text() on line 247 raises FileNotFoundError
when the file doesn't exist, before any notification is attempted.
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path so 'src' package resolves
repo_root = os.path.dirname(os.path.abspath(__file__))
for _ in range(5):
    if os.path.isdir(os.path.join(repo_root, "src")) and os.path.isfile(os.path.join(repo_root, "config.py")):
        break
    repo_root = os.path.dirname(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# --- Save environment relevant to FM_AGENT config ---
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL",
    "FM_AGENT_MODEL_BACKEND", "LLM_MODEL",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

tmpdir = None

try:
    from src.languages.erlang import ElpClient
except Exception as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)

try:
    # Create a temporary directory for the probe workspace
    tmpdir = tempfile.mkdtemp(prefix="probe_open_document_")
    nonexistent_file = Path(tmpdir) / "nonexistent_file.erl"

    # Ensure the file genuinely does not exist
    if nonexistent_file.exists():
        nonexistent_file.unlink()

    # Create an ElpClient pointing at the temp dir (no server started)
    client = ElpClient(str(tmpdir))

    # Attempt to open a non-existent document with source=None
    client.open_document(str(nonexistent_file), source=None)

    # If we reach here, no exception was raised — bug NOT confirmed
    print(
        "NOT CONFIRMED — open_document() completed without raising "
        f"FileNotFoundError for non-existent file: {nonexistent_file}"
    )

except Exception as e:
    if isinstance(e, FileNotFoundError) or (
        hasattr(e, "__class__") and e.__class__.__name__ == "FileNotFoundError"
    ):
        print(
            f"CONFIRMED — FileNotFoundError raised by open_document() "
            f"when source=None and the file does not exist. "
            f"The spec only allows exceptions for server unreachable, "
            f"notification rejection, or connection loss. "
            f"Exception: {type(e).__name__}: {e}"
        )
    elif isinstance(e, PermissionError):
        print(
            f"CONFIRMED — PermissionError raised by open_document() "
            f"when source=None and the file is not readable. "
            f"This is also a file-read exception not allowed by the spec. "
            f"Exception: {type(e).__name__}: {e}"
        )
    else:
        import traceback
        traceback.print_exc()
        print(f"ERROR: unexpected exception type: {type(e).__name__}: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]

    # Clean up temp directory
    if tmpdir:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — FileNotFoundError raised by open_document() when source=None and the file does not exist. The spec only allows exceptions for server unreachable, notification rejection, or connection loss. Exception: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/probe_open_document_mzgd9rwi/nonexistent_file.erl'
```
