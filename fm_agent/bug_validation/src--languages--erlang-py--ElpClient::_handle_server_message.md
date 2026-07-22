# Bug Report: ElpClient._handle_server_message

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When message.method is "elp/status", updates self._status to the
    value of message.params.status; if the params dict is absent or lacks
    a "status" key, self._status is unchanged
  - When message lacks an "id" field, or message.method is absent or
    falsy, no response is sent (the message is treated as a notification)
  - When message carries both a non-empty "method" and an "id" (a server
    request), sends a JSON-RPC response with jsonrpc "2.0" and the same
    id; the result value satisfies the protocol-defined expectation for
    that method:
    - For workspace configuration queries: result is a list whose length
      equals the number of requested configuration items, each element
      being null
    - For workspace folder queries: result is a singleton list containing
      the workspace-folder descriptor with the project root URI and
      directory name
    - For workspace edit requests: result indicates the edit was declined
      (applied is false)
    - For any other method the client does not handle: result is null

---

### Actual Behavior

After execution of _handle_server_message: if the incoming message's method field equals 'elp/status', the client's _status attribute is set to the value of params.get('status') (which may be None). If the message contains an 'id' and the method field is truthy (non-empty string), a JSON-RPC 2.0 response with the same id and a computed result is sent to the ELP server via the stdin pipe, using the transport protocol framing; the server will receive it as its next input. The result sent is: for 'workspace/configuration', a list of None of length equal to len(params.get('items', [])); for 'workspace/workspaceFolders', [{'uri': self.root_uri, 'name': os.path.basename(self.proj_dir)}]; for 'workspace/applyEdit', {'applied': False}; for any other method with an id, None. No response is sent if the message is a notification (no 'id') or the method is falsy. The ELP subprocess remains running and the message reader thread continues to be active. Formal logic: Let pre-state satisfy IsRunning(pre)  ThreadActive(pre)  pre_message = message. Then the post-state satisfies: IsRunning(post)  ThreadActive(post)  (self._status = pre_self._status  (message.method = 'elp/status'  self._status = message.params.get('status')))  ((('id'  message  is_truthy(message.method))   sent_response : sent_response.jsonrpc = '2.0'  sent_response.id = message.id  WrittenToStdin(sent_response)  sent_response.result = RESULT(message.method, params, self))) with RESULT =  method, params, self. case method of 'workspace/configuration'  [None | _  params.get('items', [])], 'workspace/workspaceFolders'  [{'uri': self.root_uri, 'name': os.path.basename(self.proj_dir)}], 'workspace/applyEdit'  {'applied': False}, other  None.

---

## Code Evidence

Line 198-199 (in `_handle_server_message`):
```py
if method == "elp/status":
    self._status = params.get("status")
```

The call `params.get("status")` returns `None` when params is a dict that lacks the `"status"` key. The specification requires `self._status` to **remain unchanged** in this scenario — i.e., `self._status` should only be updated when `"status"` is actually present in `params`.

---

## Trigger Condition

The code unconditionally sets self._status to params.get('status'), which evaluates to None when the 'status' key is absent or params is missing. The specification requires self._status to remain unchanged in that scenario.

---

## How to trigger the bug

Send an `"elp/status"` server notification where the `params` dict does not contain a `"status"` key. The code unconditionally sets `self._status = params.get("status")`, overwriting the previous value with `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| message.method | `"elp/status"` |
| message.params | `{"irrelevant": "data"}` (no `"status"` key) |
| self._status (before) | `"INITIAL_VALUE"` |

### Expected (spec-correct) Output

`self._status` remains `"INITIAL_VALUE"` (unchanged)

### Actual (buggy) Output

`self._status` is `None`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import queue
from unittest.mock import MagicMock
from src.languages.erlang import ElpClient

client = ElpClient("/tmp/fake_proj_dir")
client._status = "INITIAL_VALUE"
client.timeout = 5
client._send = MagicMock()
client._proc = MagicMock()

msg_queue = queue.Queue()
# Send an elp/status notification without a "status" key
msg_queue.put({"method": "elp/status", "params": {"irrelevant": "data"}})
msg_queue.put({"id": 1, "result": {}})
client._messages = msg_queue

client.request("test/method")
print(client._status)  # actual (buggy) output: None
# expected (correct) output: "INITIAL_VALUE"
```

---

## Probe Script

```py
"""Probe script for ElpClient._handle_server_message bug.

Bug: When _handle_server_message receives an "elp/status" notification where
params lacks a "status" key, it sets self._status to None (via params.get("status")).
The specification requires self._status to remain unchanged in that scenario.

We exercise the bug through the public request() API, which calls
_wait_for_response → _handle_server_message for server-initiated messages
that do not match the pending request id.
"""
import sys
import os
import queue

try:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from src.languages.erlang import ElpClient
    from unittest.mock import MagicMock

    client = ElpClient("/tmp/fake_proj_dir")
    # Set a known initial _status value
    EXPECTED_UNCHANGED = "INITIAL_VALUE"
    client._status = EXPECTED_UNCHANGED
    # Override timeout to a small value (avoids config dependency edge cases)
    client.timeout = 5
    # Prevent subprocess writes
    client._send = MagicMock()
    client._proc = MagicMock()

    # Build the message queue: first an "elp/status" notification without "status"
    # key, then a matching response so request() returns cleanly.
    msg_queue = queue.Queue()

    # Bug trigger: elp/status with params lacking "status" key
    msg_queue.put({
        "method": "elp/status",
        "params": {"irrelevant": "data"}
        # NOTE: no "status" key — spec says _status must NOT change
    })

    # Dummy response matching the request id so _wait_for_response returns
    msg_queue.put({
        "id": 1,
        "result": {}
    })
    client._messages = msg_queue

    # Exercise the buggy code path via the public API
    client.request("test/method")

    actual = client._status
    expected = EXPECTED_UNCHANGED
    passed = actual != expected  # True → bug confirmed (actual != expected)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: None | expected: 'INITIAL_VALUE'
```
