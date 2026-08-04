# Bug Report: ElpClient::initialize

**Source file:** `src/languages/erlang-py/ElpClient::initialize.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The ELP server has received the LSP initialize request conveying: the workspace root URI, the workspace folder list (containing a single folder at self.root_uri named after the project directory), client identity 'fm-agent' version '0.1.0', and requested capabilities (server status notifications, workspace configuration, hierarchical document symbols with no dynamic registration). The ELP server has received the 'initialized' notification. The text document at bootstrap_path has been opened on the server  when bootstrap_source is not None, the server uses the provided source text; when bootstrap_source is None, the server reads the file from disk. The ELP server has reached the 'running' status after processing all server messages up to and including the status transition. When the initialize response is a dict, returns the value associated with the key 'serverInfo' from that dict, or None if the key is absent. When the initialize response is not a dict, returns None. Raises an exception when the server is unreachable, when the server does not reach running status before the message-processing deadline, or when a malformed server message is received.

---

### Actual Behavior

If the method completes without raising an exception, it returns a value `server_info` equal to `(result.get('serverInfo') if isinstance(result, dict) else None)`, where `result` is the parsed JSON-RPC response of the 'initialize' request. The server connection remains active, the 'initialized' notification has been sent, the document at `bootstrap_path` has been opened (using `bootstrap_source` if not None, otherwise referencing the file on disk), and `str(self._status).lower() == 'running'` holds, meaning the server has reached the running state. The polling loop was bounded by a deadline of `time.monotonic() + self.timeout`. If any step fails (server unreachable, JSON-RPC error response, connection loss, message timeout, or malformed server message), an exception is raised and the method does not return; the state of the client and server may be inconsistent. Formally: Pre(self, bootstrap_path, bootstrap_source)  ((NormalReturn  ( server_info: return_value = server_info  server_info = (resp['serverInfo'] if isinstance(resp, dict) else None)  self.connection_active  str(self._status).lower() = 'running'  notified('initialized')  doc_opened(bootstrap_path, bootstrap_source)))  (Exception  )).

---

## Code Evidence

Line 2:         result = self.request(

---

## Trigger Condition

The specification lists only three specific conditions under which an exception is raised: server unreachable, server does not reach running status before deadline, or malformed server message. The code raises an exception when the server returns a JSON-RPC error response (e.g., 'Method not found') which does not fall under any of those conditions. According to the specification, the method should return server_info in all other cases, so a JSON-RPC error leads to a mismatch.

---

## How to trigger the bug

When the ELP server returns a JSON-RPC error response (e.g. `{"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"Method not found"}}`) in reply to the `initialize` request, `ElpClient._wait_for_response()` raises `RuntimeError(f"ELP request failed: {error}")` at line 189 of `src/languages/erlang.py`. The specification enumerates three exception-raising conditions — server unreachable, timeout, and malformed server messages — and a JSON-RPC error response does not match any of them. The spec therefore implies the method should return a normal value (e.g. `None`) in this case, but the code raises an exception instead.

### Inputs

| Parameter | Value |
|-----------|-------|
| `bootstrap_path` | `"/tmp/test.erl"` |
| `bootstrap_source` | `"-module(test)."` |
| Simulated server response | `{"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"Method not found"}}` |

### Expected (spec-correct) Output

`None` — the spec does not list JSON-RPC error response as an exception-raising condition, so the method should return normally.

### Actual (buggy) Output

`RuntimeError("ELP request failed: {'code': -32601, 'message': 'Method not found'}")` — the code raises an exception on any non-`_ContentModifiedError` JSON-RPC error response.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import queue
from unittest.mock import MagicMock
import src.languages.erlang as erlang

error_msg = {"jsonrpc":"2.0","id":1,"error":{"code":-32601,"message":"Method not found"}}

client = erlang.ElpClient.__new__(erlang.ElpClient)
client.proj_dir = "/tmp/test"
client.root_uri = "file:///tmp/test"
client.timeout = 60
client._messages = queue.Queue()
client._next_id = 1
client._status = None
client._write_lock = MagicMock()
client._proc = MagicMock()
client._proc.stdin = MagicMock()
client._reader = MagicMock()

client._messages.put(error_msg)
client.initialize("/tmp/test.erl", "-module(test).")
# actual (buggy) output: RuntimeError("ELP request failed: {'code': -32601, 'message': 'Method not found'}")
# expected (correct) output: None (no exception)
```

---

## Probe Script

```python
"""Probe for bug src--languages--erlang-py--ElpClient::initialize.

Bug: initialize() raises RuntimeError when ELP returns a JSON-RPC error response
(e.g. "Method not found"), but the spec says exceptions are only raised for:
server unreachable, timeout, or malformed server messages.
"""

import os
import sys
import queue
import tempfile
from unittest.mock import MagicMock

# Ensure the repo root is on sys.path so that config.py resolves.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import src.languages.erlang as erlang  # public entry point

# FM-Agent self-validation guard: work in a fresh temp directory.
_original_cwd = os.getcwd()
_temp_dir = tempfile.mkdtemp(prefix="probe_erlang_init_")
os.chdir(_temp_dir)

try:
    # Simulated JSON-RPC error response from ELP (e.g. "Method not found").
    error_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32601, "message": "Method not found"},
    }

    # Construct ElpClient without spawning a real subprocess.
    client = erlang.ElpClient.__new__(erlang.ElpClient)
    client.proj_dir = _temp_dir
    client.root_uri = "file://" + _temp_dir
    client.timeout = 60
    client._messages = queue.Queue()
    client._next_id = 1
    client._status = None
    client._write_lock = MagicMock()
    client._proc = MagicMock()
    client._proc.stdin = MagicMock()
    client._reader = MagicMock()

    # Pre-seed the message queue so _wait_for_response sees the error.
    client._messages.put(error_msg)

    # Call the public initialize() — this must raise RuntimeError.
    result = client.initialize("/tmp/test.erl", "-module(test).")
    print(f"NOT CONFIRMED — no exception raised, returned: {result!r}")
except RuntimeError as exc:
    print(f"CONFIRMED — bug confirmed: RuntimeError raised for JSON-RPC error response: {exc}")
except Exception as exc:
    print(f"CONFIRMED — exception raised: {type(exc).__name__}: {exc}")
finally:
    os.chdir(_original_cwd)
    import shutil
    shutil.rmtree(_temp_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — bug confirmed: RuntimeError raised for JSON-RPC error response: ELP request failed: {'code': -32601, 'message': 'Method not found'}
```
