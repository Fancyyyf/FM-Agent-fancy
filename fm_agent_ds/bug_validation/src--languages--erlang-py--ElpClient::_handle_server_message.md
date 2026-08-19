# Bug Report: ElpClient::_handle_server_message

**Source file:** `src/languages/erlang-py/ElpClient::_handle_server_message.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When message has a 'method' key with value 'elp/status' and a 'params' key, self._status is updated to the value of params['status'] (or a falsy default if 'status' is absent from params). When message has both an 'id' key and a truthy 'method' key, a JSON-RPC 2.0 response is sent via self._send with: 'jsonrpc' set to '2.0', 'id' set to message['id'], and 'result' determined by the method  for 'workspace/configuration', result is a list of None values whose length equals the count of entries in params['items'] (or a zero-length list if 'items' is absent from params); for 'workspace/workspaceFolders', result is a list containing a single dict with 'uri' set to self.root_uri and 'name' set to the last path component of self.proj_dir; for 'workspace/applyEdit', result is {'applied': False}; for any other method, result is None. When message lacks an 'id' key or lacks a truthy 'method' key, no response is sent. The function returns None.

---

### Actual Behavior

Natural language: After method execution, if the message 'method' is 'elp/status', self._status is updated to the value associated with 'status' in params (or None if not present), where params defaults to {} if absent. If the message contains an 'id' key and a truthy 'method' value, a JSON-RPC response is sent via self._send with 'jsonrpc':'2.0', 'id':message['id'], and 'result' computed as: if method=='workspace/configuration' then a list of None of length equal to len(items) with items from params (or [] if absent); if method=='workspace/workspaceFolders' then [{'uri':self.root_uri,'name':os.path.basename(self.proj_dir)}]; if method=='workspace/applyEdit' then {'applied':False}; otherwise None. If the message lacks an 'id' or the method is falsey, no response is sent. No other attributes are modified, and no exceptions are raised. Formal: (message.method = 'elp/status'  self._status = (params.status if paramsdict else None))  ((message.method = 'elp/status')  self._status = self._status_pre)  (('id'message  message.id  None  message.method  None  message.method  '')   r : (r = case message.method of 'workspace/configuration': [None | _  items] where items = params.get('items',[]); 'workspace/workspaceFolders': [{'uri':self.root_uri,'name':os.path.basename(self.proj_dir)}]; 'workspace/applyEdit': {'applied':False}; other: None)  self._send({'jsonrpc':'2.0','id':message.id,'result':r}) )  (('id'message  message.method truthy)  m s.t. self._send(m))

---

## Code Evidence

Line 4:         if params is None:
Line 5:             params = {}
Line 7:             self._status = params.get("status")

---

## Trigger Condition

The specification requires self._status to be updated only when the message contains a 'params' key. The code defaults a missing 'params' to an empty dict, causing self._status to be unconditionally set to None (or another falsy value) even when no 'params' key is present, which violates the specification.

---

## How to trigger the bug

When an ElpClient instance receives a server message with `method="elp/status"` but **without** a `"params"` key, the specification requires `self._status` to remain unchanged. However, the code defaults `params` to `{}` when missing, and then unconditionally executes `self._status = params.get("status")`, which overwrites `self._status` with `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| message | `{"method": "elp/status"}` |
| self._status (before) | `"INITIAL_SENTINEL"` |

### Expected (spec-correct) Output

`self._status` should remain `"INITIAL_SENTINEL"` (unchanged, because the message lacks a `"params"` key).

### Actual (buggy) Output

`self._status` is overwritten to `None`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
from src.languages.erlang import ElpClient

client = ElpClient("/tmp/test_proj")
client._status = "INITIAL_SENTINEL"  # sentinel to detect overwrite
client._handle_server_message({"method": "elp/status"})
print(client._status)
# actual (buggy) output: None
# expected (correct) output: INITIAL_SENTINEL
```

---

## Probe Script

```python
"""Probe script for ElpClient._handle_server_message bug.

Bug: When message has method="elp/status" but NO "params" key, the spec says
self._status should NOT be updated. The code defaults missing params to {},
causing self._status to be unconditionally set to None (via {}.get("status")),
violating the specification.

FM-Agent self-validation: tests the smallest unit (ElpClient instance without
starting ELP subprocess), per the self-validation guard.
"""

import sys
import os
import tempfile

# Add repo root to Python path so the 'src' package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.languages.erlang import ElpClient

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an ElpClient without starting it (no __enter__).
        # __init__ sets _status to None via normal flow, so we must
        # reassign to a sentinel before the test call.
        client = ElpClient(os.path.join(tmpdir, "dummy_proj"))

        # Set _status to a known sentinel value to detect overwrite
        client._status = "INITIAL_SENTINEL"

        # Message: method="elp/status", no "params" key, no "id" key
        # Spec: _status should NOT change (requires "params" key present)
        # Code (buggy): _status gets set to None when "params" key is absent
        message = {"method": "elp/status"}

        client._handle_server_message(message)

        # Per spec: _status should remain "INITIAL_SENTINEL" when "params" is absent
        # Per code: _status is overwritten to None
        if client._status == "INITIAL_SENTINEL":
            print(
                "NOT CONFIRMED — _status remained unchanged ('INITIAL_SENTINEL') "
                "when 'params' key was absent, which matches the specification."
            )
        else:
            print(
                f"CONFIRMED — _status was overwritten to {client._status!r} from "
                f"'INITIAL_SENTINEL' despite the message lacking a 'params' key. "
                f"The specification requires _status to be updated ONLY when the "
                f"message contains a 'params' key."
            )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — _status was overwritten to None from 'INITIAL_SENTINEL' despite the message lacking a 'params' key. The specification requires _status to be updated ONLY when the message contains a 'params' key.
```
