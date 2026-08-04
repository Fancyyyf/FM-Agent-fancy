# Bug Report: ElpClient::_wait_for_response

**Source file:** `src/languages/erlang-py/ElpClient::_wait_for_response.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the 'result' field of the server's JSON-RPC response whose 'id' equals request_id and which lacks a 'method' key. If the matching response contains an 'error' object whose 'code' field equals the content-modified error code, raises _ContentModifiedError. If the matching response contains any other 'error' object, raises RuntimeError with a message describing the error. Messages from the server that do not match request_id  including server notifications identified by the presence of a 'method' key  are delegated to message handling without returning control to the caller.

---

### Actual Behavior

After execution of `_wait_for_response`, if no exception is raised, the returned value is the 'result' field of a JSONRPC response message that has `id` equal to the given `request_id`, has no `'method'` key, and contains no `'error'` field. All server messages received before that response (i.e., messages with a different `id` or containing a `'method'` key) have been processed by `_handle_server_message`. If a `_ContentModifiedError` is raised, then the response for `request_id` contained an `'error'` field that is a dictionary with `'code'` equal to `_CONTENT_MODIFIED_ERROR`. If a `RuntimeError` is raised, then the response contained an `'error'` that does not match that specific code. If an exception is raised from `self._next_message(deadline)`, then either the deadline was reached without receiving a message or the server connection was lost. Formal logic: Let `M` be the last message retrieved by `self._next_message` before the method exits.
- (return `r`)  `M.get('id') == request_id  'method'  M.keys()  M.get('error') is None  r == M.get('result')  M' received earlier: (M'.get('id') != request_id  'method'  M'.keys())  processed_by_handle(M')`.
- (_ContentModifiedError)  `M.get('id') == request_id  'method'  M.keys()  isinstance(M.get('error'), dict)  M.get('error').get('code') == _CONTENT_MODIFIED_ERROR`.
- (RuntimeError)  `M.get('id') == request_id  'method'  M.keys()  M.get('error') is not None  (isinstance(M.get('error'), dict)  M.get('error').get('code') == _CONTENT_MODIFIED_ERROR)`.
- (exception from `_next_message`)  no message satisfying the response condition was received before `deadline` or the connection was lost.

---

## Code Evidence

Line 6: if error:

---

## Trigger Condition

An error object that is an empty dict is falsy in Python, causing the code to skip error handling and return the result. However, the specification requires that any error object other than the specific content-modified one must raise RuntimeError. This violates the specification when a matching response contains an empty 'error' object.

---

## How to trigger the bug

The bug is triggered when the `_wait_for_response` method receives a JSON-RPC response message whose `id` matches `request_id`, has no `"method"` key, and contains an `"error"` field whose value is an empty dictionary `{}`. In Python, an empty dict is falsy, so the `if error:` check on line 186 evaluates to `False`, skipping error handling entirely. The method then falls through to `return message.get("result")` which returns `None` (since the error response has no `"result"` field), instead of raising `RuntimeError` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `request_id` | `1` |
| `deadline` | `time.monotonic() + 10` (any future time) |
| Message returned by `_next_message` | `{"jsonrpc": "2.0", "id": 1, "error": {}, "result": None}` |

### Expected (spec-correct) Output

`RuntimeError` raised with message `"ELP request failed: {}"` — because the `"error"` field is present (`{}` is not `None`) and its code is not `_CONTENT_MODIFIED_ERROR`.

### Actual (buggy) Output

`None` — the empty dict `{}` is falsy, so `if error:` is `False`, bypassing the error-raising code and falling through to `return message.get("result")` which is `None`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import ElpClient
import time

client = ElpClient("/tmp/fake_proj_dir")
crafted = {"jsonrpc": "2.0", "id": 1, "error": {}, "result": None}
client._next_message = lambda deadline: crafted
result = client._wait_for_response(1, time.monotonic() + 10)
print(result)  # actual (buggy) output: None
# expected (correct) output: RuntimeError: ELP request failed: {}
```

---

## Probe Script

```python
"""Probe script for bug: ElpClient._wait_for_response - empty error dict bypasses error handling.

Bug ID: src--languages--erlang-py--ElpClient::_wait_for_response
Source: src/languages/erlang.py, line 186: `if error:` treats empty dict {} as falsy.
Spec: Any error object other than ContentModifiedError must raise RuntimeError.
Bug: Empty error dict {} is falsy, so error handling is skipped and message.get("result") is returned.
"""
import sys
import time

try:
    from src.languages.erlang import ElpClient

    # Create an ElpClient instance without starting a subprocess.
    # We avoid __enter__ to not require ELP to be installed.
    client = ElpClient("/tmp/fake_proj_dir")

    # Craft a JSON-RPC response message that matches request_id=1,
    # has no "method" key, and contains an empty error dict {}.
    # An empty dict is falsy in Python, which triggers the bug.
    crafted_response = {"jsonrpc": "2.0", "id": 1, "error": {}, "result": None}

    # Monkey-patch _next_message to return the crafted response
    # so we can exercise _wait_for_response without a real ELP server.
    original_next_message = client._next_message
    client._next_message = lambda deadline: crafted_response

    try:
        actual = client._wait_for_response(1, time.monotonic() + 10)
        # If we reach here, no exception was raised — the bug is confirmed.
        # The spec demands RuntimeError for any error that isn't _ContentModifiedError.
        passed = True  # Bug reproduced: empty error dict bypassed error handling
    except RuntimeError as e:
        # The code correctly raised a RuntimeError (bug NOT confirmed / already fixed)
        actual = f"RuntimeError: {e}"
        passed = False
    except Exception as e:
        print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        # Restore original method
        client._next_message = original_next_message

    expected = "RuntimeError for any non-content-modified error object"

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: None | expected: RuntimeError for any non-content-modified error object
```
