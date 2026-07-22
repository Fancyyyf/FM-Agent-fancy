# Bug Report: ElpClient.open_document

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Transmits a "textDocument/didOpen" notification to the ELP server
    whose textDocument field is a dict containing:
      - uri: the absolute file:// URI representing the path argument
      - languageId: "erlang"
      - version: 1
      - text: source when source is provided; otherwise the UTF-8 text
        content of the file at path
  - When source is None and the file at path cannot be read, the
    underlying IOError propagates to the caller

---

### Actual Behavior

The ElpClient's underlying JSON-RPC communication channel remains open and writable. A JSON-RPC 2.0 notification message with method "textDocument/didOpen" has been transmitted. The message params contain a single key "textDocument" whose value is a dictionary with keys: "uri" set to the URI of the resolved absolute path of `path` (i.e., `Path(path).resolve().as_uri()`), "languageId" set to "erlang", "version" set to 1, and "text" set to the string content provided by `source` if `source` was not None, or to the entire contents of the file at the resolved path read as UTF-8 text with replacement for decoding errors if `source` was None. The local variable `document` holds the resolved absolute `Path` object, and the local variable `source` holds the text content that was sent (either the original argument or the file contents). No return value is produced. Formal: ( ch = self.communication_channel . is_open(ch)  writable(ch))  ( msg = notification(method: "textDocument/didOpen", params: { "textDocument": { uri: document.as_uri(), languageId: "erlang", version: 1, text: source_text } }) . transmitted(ch, msg)) where document = resolve(Path(path))  source_text = (if source_arg  None then source_arg else read_text(document, encoding="utf-8", errors="replace"))  source_arg = original `source` binding on entry.

---

## Code Evidence

Line 2:         document = Path(path).resolve()

---

## Trigger Condition

The code uses Path(path).resolve() which resolves symbolic links, so the resulting URI does not represent the original path argument as required by the specification. The specification requires the absolute file:// URI to represent the path argument, not its resolved target.

---

## How to trigger the bug

When `open_document` is called with a `path` argument that is a symbolic link, the code calls `Path(path).resolve()` which follows the symlink to its target. The resulting URI points to the symlink's target file, not the symlink itself. The spec requires the URI to represent the `path` argument as given.

### Inputs

| Parameter | Value |
|-----------|-------|
| path | A string path to a symbolic link (e.g., `/tmp/test/link.erl` → `/tmp/test/real.erl`) |
| source | None (default — triggers file read) |

### Expected (spec-correct) Output

The URI in the notification should be `file:///tmp/test/link.erl` (the original `path` argument).

### Actual (buggy) Output

The URI in the notification is `file:///tmp/test/real.erl` (the resolved symlink target).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from pathlib import Path
from src.languages.erlang import ElpClient

import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    real_file = Path(tmpdir) / "real.erl"
    real_file.write_text("-module(real).")
    symlink = Path(tmpdir) / "link.erl"
    symlink.symlink_to(real_file)

    client = ElpClient(tmpdir)
    captured = []

    # Monkey-patch notify to intercept the URI
    original = client.notify
    client.notify = lambda m, p: captured.append(p)

    client.open_document(str(symlink))
    # actual (buggy) URI: captured[0]['textDocument']['uri']
    #   -> 'file:///tmp/.../real.erl'  (symlink target)
    # expected (correct) URI:
    #   -> 'file:///tmp/.../link.erl'  (the path argument)
```

---

## Probe Script

```python
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add snapshot root to path for imports
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

from src.languages.erlang import ElpClient

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a real file with content so read_text doesn't fail
        real_file = Path(tmpdir) / "real.erl"
        real_file.write_text("-module(real).\n-export([hello/0]).\n\nhello() -> ok.\n")

        # Create a symlink pointing to the real file
        symlink = Path(tmpdir) / "link.erl"
        symlink.symlink_to(real_file)

        # Instantiate ElpClient — constructor does NOT spawn a subprocess
        # (only __enter__ does that, so this is safe)
        client = ElpClient(tmpdir)

        # Mock notify to capture the params argument
        captured_params = [None]

        def capture_notify(method, params):
            captured_params[0] = params

        with patch.object(client, 'notify', side_effect=capture_notify):
            client.open_document(str(symlink))

        # Extract the URI that was sent
        actual_uri = captured_params[0]['textDocument']['uri']

        # The spec says URI must represent the "path argument" (the symlink),
        # but resolve() follows symlinks to the target.
        expected_uri = symlink.as_uri()

        passed = actual_uri != expected_uri

        if passed:
            print(f'CONFIRMED — actual URI: {actual_uri!r} | expected URI: {expected_uri!r}')
        else:
            print(f'NOT CONFIRMED — actual URI matched expected: {actual_uri!r}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual URI: 'file:///tmp/tmpn3s6sqex/real.erl' | expected URI: 'file:///tmp/tmpn3s6sqex/link.erl'
```
