# Bug Report: ElpClient::initialize

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/ElpClient::initialize.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Completes the LSP initialization handshake: sends the "initialize"
    request with client capabilities, then sends the "initialized"
    notification
  - Opens the document at bootstrap_path on the server with the text content
    matching bootstrap_source (or the file contents of bootstrap_path when
    bootstrap_source is None)
  - Blocks until the server's reported status indicates it has reached a
    running state, or raises TimeoutError when that does not occur within
    self.timeout seconds measured from the call entry
  - Returns the "serverInfo" sub-dict from the server's "initialize"
    response, or None when the response is missing, is not a dict, or does
    not contain a "serverInfo" key
  - Raises RuntimeError when the ELP subprocess is not running (stdin
    unavailable) or the JSON-RPC channel encounters an unrecoverable error
  - Raises TimeoutError when the server fails to reach the running state
    within the deadline or the subprocess stops producing messages

---

### Actual Behavior

If the method returns normally, then the return value is (R.get('serverInfo') if type(R) == dict else None) where R is the 'result' field of the JSON-RPC 'initialize' response; the 'initialize' request, the 'initialized' notification, and the 'textDocument/didOpen' notification for bootstrap_path were all successfully sent; the while loop processed server messages until str(self._status).lower() == 'running', so self._status indicates 'running'; all server requests received before that status were appropriately responded to, and any 'elp/status' notifications updated self._status. The deadline for message reception was fixed at loop entry (time.monotonic() + self.timeout). If the method raises an exception, it is either TimeoutError (from request or _next_message exceeding self.timeout), RuntimeError (from request error, retry exhaustion, notify failure, or reader thread exception), or IOError (from open_document when bootstrap_source is None and the file cannot be read), and the client state may be partially modified (e.g., 'initialize' sent but status not 'running'). Formal: (return(server_info)  exception)  (R: R = request('initialize',...).result  server_info = (R.get('serverInfo') if dict(R) else None)  sent('initialized')  sent(didOpen(bootstrap_path,...))  (str(self._status).lower() = 'running')  m  received_before('running'): handled(m)). If exception e raised, then e  {TimeoutError, RuntimeError, IOError}  (some_side_effects  none).

---

## Code Evidence

Line 26: deadline = time.monotonic() + self.timeout

---

## Trigger Condition

The specification requires that the timeout deadline be measured from the call entry, but the code sets it after the initialize request and open_document, potentially allowing the method to succeed when it should time out.

---

## How to trigger the bug

The `deadline` variable on line 239 of `src/languages/erlang.py` (line 26 in the extracted function) is computed after `self.request("initialize", ...)` (which can block for up to `self.timeout` seconds), `self.notify("initialized")`, and `self.open_document()`. The specification requires the timeout to be measured from the `initialize` method's call entry, so the effective timeout window is `self.timeout + time_spent_in_request_and_handshake` instead of just `self.timeout`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self.timeout` | `1.0` |
| Injected delay in `request()` | `0.6s` |
| `bootstrap_path` | `"/tmp/bootstrap.erl"` |
| `bootstrap_source` | `"-module(bootstrap)."` |

### Expected (spec-correct) Output

`deadline = entry_time + self.timeout` (timeout measured from call entry)

### Actual (buggy) Output

`deadline ≈ entry_time + request_delay + self.timeout` (timeout measured after handshake completes)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import ElpClient
import time

client = ElpClient.__new__(ElpClient)
client.proj_dir = "/tmp/test"
client.root_uri = "file:///tmp/test"
client.timeout = 1.0
client._messages = ...
# Set up all required attributes manually or via __init__ with a temp dir

entry_time = time.monotonic()

# Override request to simulate a slow handshake
def fake_request(method, params=None):
    time.sleep(0.6)
    return {"serverInfo": {"name": "elp", "version": "1.0"}}

client.request = fake_request
client.notify = lambda *a, **kw: None
client.open_document = lambda *a, **kw: None
client._handle_server_message = lambda msg: None

captured = []
def capture_next_message(deadline):
    captured.append(deadline)
    client._status = "running"
    return {}

client._next_message = capture_next_message

client.initialize("/tmp/bootstrap.erl", "-module(bootstrap).")

# actual (buggy) output: captured[0] ≈ entry_time + 0.6 + 1.0
# expected (correct) output: captured[0] = entry_time + 1.0
```

---

## Probe Script

```python
"""Probe for ElpClient.initialize bug: deadline computed after request(), not from call entry."""

import os
import sys
import tempfile
import time

bug_id = "src--languages--erlang-py--ElpClient::initialize"

# Ensure the repo root is on sys.path so we can import the package.
repo_root = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../..")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Create a fresh temporary workspace for all fixtures and artifacts.
workspace = tempfile.mkdtemp(prefix="bug_probe_", dir="/tmp")
os.chdir(workspace)

try:
    from src.languages.erlang import ElpClient

    client = ElpClient(workspace)
    client.timeout = 1.0  # known short timeout for deterministic test

    # Override request(): simulate a slow LSP initialize handshake that
    # consumes most of the timeout budget before the deadline is even set.
    def fake_request(method, params=None):
        time.sleep(0.6)  # 60% of the 1s timeout wasted before deadline is computed
        return {"serverInfo": {"name": "elp", "version": "1.0"}}

    client.request = fake_request

    # Remaining methods must be no-ops so we don't hit real I/O.
    client.notify = lambda method, params=None: None
    client.open_document = lambda path, source=None: None

    # _handle_server_message is a no-op; we control status directly in _next_message.
    client._handle_server_message = lambda msg: None

    # Override _next_message to capture the deadline and transition status to "running".
    captured_deadlines = []

    def capture_next_message(deadline):
        captured_deadlines.append(deadline)
        # Simulate an elp/status notification that makes the while-loop exit.
        client._status = "running"
        return {"method": "elp/status", "params": {"status": "running"}}

    client._next_message = capture_next_message

    entry_time = time.monotonic()
    client.initialize("/tmp/bootstrap.erl", "-module(bootstrap).")

    if len(captured_deadlines) == 0:
        print("NOT CONFIRMED — _next_message was never called")
        sys.exit(0)

    actual_deadline = captured_deadlines[0]
    expected_deadline = entry_time + client.timeout

    # The spec requires the deadline to be measured from call entry.
    # The buggy code measures it after request(), so actual_deadline is
    # entry_time + request_delay + timeout instead of entry_time + timeout.
    tolerance = 0.2  # allow for slight timing jitter
    if actual_deadline > expected_deadline + tolerance:
        delta = actual_deadline - expected_deadline
        print(
            f"CONFIRMED — actual deadline: {actual_deadline:.3f}"
            f" > expected: {expected_deadline:.3f}"
            f" (delta: {delta:.3f}s, spec requires deadline from call entry)"
        )
    else:
        print(
            f"NOT CONFIRMED — actual deadline {actual_deadline:.3f}"
            f" <= expected {expected_deadline:.3f} (+{tolerance}s tolerance)"
        )

except ImportError as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    import shutil
    try:
        shutil.rmtree(workspace, ignore_errors=True)
    except Exception:
        pass
```

### Probe Output

```
CONFIRMED — actual deadline: 6546.858 > expected: 6546.257 (delta: 0.601s, spec requires deadline from call entry)
```
