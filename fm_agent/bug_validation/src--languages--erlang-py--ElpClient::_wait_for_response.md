# Bug Report: ElpClient._wait_for_response

**Source file:** `src/languages/erlang-py/ElpClient::_wait_for_response.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Blocks the caller, consuming messages from the underlying channel in
    order until a JSON-RPC response carrying a matching id field arrives
  - A message is considered a matching response when its "id" field equals
    request_id and the message lacks a "method" field, distinguishing
    server responses from server-initiated requests and notifications
  - Messages received from the server that are not the matching response
    are forwarded for server-initiated handling and do not cause the
    function to return
  - When the underlying channel closes or no message arrives before
    deadline: raises TimeoutError
  - When the matching response contains an "error" field:
       If the error is a dict whose "code" field equals the transient
        content-modified error code: raises _ContentModifiedError carrying
        the error details
       Otherwise: raises RuntimeError whose message includes a
        description of the error
  - When the matching response contains no "error" field: returns the
    value of the "result" field from that response

---

### Actual Behavior

If a JSON-RPC response message m with m['id'] == request_id and 'method' not in m is received before the absolute monotonic time deadline, then the method either returns m['result'] if m contains no 'error' field or 'error' is null, raises _ContentModifiedError(m['error']) if m['error'] is a dict with key 'code' equal to _CONTENT_MODIFIED_ERROR, or raises RuntimeError('ELP request failed: {error}') for any other non-null 'error'. If no such matching response is received before deadline, TimeoutError is raised. During execution, every message received from the server that does not satisfy the matching condition is passed to self._handle_server_message, which processes it according to registered handlers, mutating the client state appropriately, and is guaranteed not to raise an exception under normal operation. The underlying communication channel remains open and operational unless one of those handlers causes a fatal exception, in which case the exception propagates uncaught. Formally, let the incoming message stream be an ordered sequence M of parsed message dictionaries. Let P be the longest prefix of M that does not contain a message with 'id' == request_id and lacking 'method', and that is fully consumed before deadline. The execution processes all messages in P via _handle_server_message, producing intermediate state S_i. If the first message after P is m* that satisfies the matching condition and arrives  deadline, then the outcome is return(m*.get('result')) or raise exception as above, with the client state advanced accordingly. If no such m* exists before the deadline, the outcome is raise TimeoutError, and the state after processing P is the final state. In all cases, no other side effects on the ElpClient or its channel occur.

---

## Code Evidence

Line 6: if error:

---

## Trigger Condition

The code checks truthiness of the 'error' value with 'if error:', which is False for None (and other false-like values). The specification requires that any matching response containing an 'error' field raises an exception (RuntimeError if not the specific content-modified error). Thus, for a response with error=null, the code incorrectly returns the 'result' instead of raising RuntimeError.

---

## How to trigger the bug

A JSON-RPC response message with `"error": null` (JSON `null`, parsed as Python `None`) that matches the pending `request_id` and lacks a `"method"` field will cause `_wait_for_response` to return the `"result"` value instead of raising `RuntimeError`. The truthiness check `if error:` on line 186 of `src/languages/erlang.py` treats `None` as falsy, so it falls through to `return message.get("result")`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `request_id` | `42` |
| `deadline` | `time.monotonic() + 10.0` |
| Injected message | `{"jsonrpc": "2.0", "id": 42, "error": None, "result": "some_value"}` |

### Expected (spec-correct) Output

`RuntimeError("ELP request failed: None")` — the specification states that any matching response containing an `"error"` field must raise `RuntimeError` unless it is the specific content-modified error code.

### Actual (buggy) Output

`'some_value'` — the method returns the value of the `"result"` field because `if error:` evaluates to `False` when `error` is `None`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile, queue, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.languages.erlang import ElpClient

client = ElpClient(tempfile.mkdtemp(prefix="fm-agent-probe-"))
client._messages.put({
    "jsonrpc": "2.0",
    "id": 42,
    "error": None,
    "result": "some_value",
})
result = client._wait_for_response(42, time.monotonic() + 10.0)
print(result)
# actual (buggy) output: 'some_value'
# expected (correct) output: RuntimeError("ELP request failed: None")
```

---

## Probe Script

```python
"""Probe script for ElpClient._wait_for_response bug.

Bug: When a JSON-RPC response carries "error": null, the code checks
truthiness with `if error:` (line 186 of src/languages/erlang.py) and
fall through to `return message.get("result")` instead of raising
RuntimeError as the specification requires.
"""

import sys
import os

# Ensure the repo root is on the path so the package entry point resolves.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tempfile
import queue
import time

try:
    from src.languages.erlang import ElpClient
except Exception as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)

# ── Construct a minimal ElpClient without launching ELP ──────────────────
client = ElpClient(tempfile.mkdtemp(prefix="fm-agent-probe-"))

# Seed the message queue with a matching JSON-RPC response whose "error"
# field is explicitly null (Python None).  The spec requires this to raise
# RuntimeError; the buggy code will return the "result" value instead.
request_id = 42
deadline = time.monotonic() + 10.0

client._messages.put({
    "jsonrpc": "2.0",
    "id": request_id,
    "error": None,          # ← null in JSON-RPC → None in Python
    "result": "some_value",
})
# No "method" key → the response is recognised as a server response.

# ── Exercise the buggy code path ────────────────────────────────────────
actual = None
raised = None

try:
    actual = client._wait_for_response(request_id, deadline)
except RuntimeError as exc:
    raised = exc
except Exception as exc:
    print(f"ERROR: Unexpected exception: {exc}")
    sys.exit(1)

# ── Oracle ──────────────────────────────────────────────────────────────
# Specification: "When the matching response contains an 'error' field …
#   Otherwise: raises RuntimeError whose message includes a description of
#               the error"
# Bug: the code returns result when error is None (falsy).
#
# If `_wait_for_response` returned a value (actual is not None and no
# exception) → the bug is **CONFIRMED** because the spec requires a raise.
#
# If it raised RuntimeError → NOT CONFIRMED (the code behaves correctly
# for this input).

if raised is None and actual is not None:
    # Bug reproduced: code returned result instead of raising.
    print(f"CONFIRMED — actual returned: {actual!r} | expected: RuntimeError (per spec)")
else:
    print(f"NOT CONFIRMED — actual raised: {raised!r}")
```

### Probe Output

```
CONFIRMED — actual returned: 'some_value' | expected: RuntimeError (per spec)
```
