# Bug Report: ElpClient._next_message

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When a message is available before the monotonic clock reaches
    deadline, returns the next pending parsed JSON-RPC response or
    notification message from the server as a dict whose shape conforms
    to the JSON-RPC 2.0 specification
  - Raises TimeoutError when no message is available before the
    monotonic clock reaches deadline, including when the deadline has
    already passed at call entry
  - Raises RuntimeError when the message reader thread terminated with
    an unrecoverable exception; the original exception from the reader
    thread is chained as the cause of the RuntimeError

---

### Actual Behavior

After the method executes, exactly one of the following outcomes occurs:

1. Normal return: The method returns a message `msg`. `msg` is not an instance of `BaseException`. It was removed from `self._messages` before `deadline` (i.e., at some instant `t` with `t <= deadline`). The internal queue after the call contains every element that was enqueued by the reader thread during the call except `msg`. The monotonic clock at the return point satisfies `time.monotonic() <= deadline`.

2. TimeoutError raised: A `TimeoutError` is raised. No element was removed from `self._messages` before `deadline`. The queue after the call is unchanged apart from any new elements added by the reader thread. At the moment the exception is raised, `time.monotonic() >= deadline`.

3. RuntimeError raised: A `RuntimeError` is raised, chained from a `BaseException` `e`. `e` was removed from `self._messages` before `deadline`. The queue after the call contains every other element enqueued by the reader thread during the call. The removal occurs at some instant `t` with `t <= deadline`.

The active message reader thread continues to run and may keep enqueuing parsed JSON-RPC messages or exceptions into `self._messages`.

---

## Code Evidence

Line 11: return message

---

## Trigger Condition

The specification requires the method to return a dict that conforms to the JSON-RPC 2.0 specification. The code, however, returns any non-BaseException object from the queue without checking that it is a dict, thus violating the specification for any input where the queue contains a non-dict non-exception value.

---

## How to trigger the bug

The bug is triggered when the internal message queue (`self._messages`) contains a value that is not a `BaseException` but is also not a `dict`. The `_next_message` method only checks `isinstance(message, BaseException)` before returning, missing the dict-type validation required by the spec. In practice, this could occur if the ELP JSON-RPC reader (`_JsonRpcReader`) parses a malformed LSP payload that is valid JSON but not a JSON object — for example, a JSON array `[1, 2, 3]`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self._messages` (queue) | Contains item `[1, 2, 3]` (a list) |
| `deadline` | `time.monotonic() + 30.0` |

### Expected (spec-correct) Output

Either a `dict` conforming to JSON-RPC 2.0, a `TimeoutError`, or a `RuntimeError`. A non-dict value should not be returned.

### Actual (buggy) Output

Returns `[1, 2, 3]` (type: `list`) — a non-dict value passed through without validation.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import queue
import time
from src.languages.erlang import ElpClient

client = ElpClient('/tmp/test')
client._messages.put([1, 2, 3])  # non-dict value
result = client._next_message(time.monotonic() + 30.0)
# actual (buggy) output: [1, 2, 3]
# expected (correct) output: raises an error (the value is not a JSON-RPC 2.0 dict)
```

---

## Probe Script

```python
"""Probe for ElpClient._next_message bug: returns non-dict values without validation."""

import os
import queue
import sys
import tempfile
import time

# Ensure the repo root is on sys.path so we can import the package.
repo_root = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + "/../..")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Create a fresh temporary workspace for all fixtures and artifacts.
workspace = tempfile.mkdtemp(prefix="bug_probe_", dir="/tmp")
os.chdir(workspace)

try:
    from src.languages.erlang import ElpClient

    # Spec claim: _next_message must return a dict conforming to JSON-RPC 2.0,
    # or raise TimeoutError/RuntimeError.

    # Trigger condition: the queue contains a non-dict, non-BaseException value
    # (e.g., a list). The code returns it without checking that it is a dict.

    # Create an ElpClient in a temp dir — __init__ only sets up attributes,
    # it does not spawn ELP.
    client = ElpClient(workspace)
    actual = None
    passed = False

    # Put a non-dict value (a list) into the internal message queue.
    buggy_payload = [1, 2, 3]  # not a dict
    client._messages.put(buggy_payload)

    # Set a deadline far in the future to avoid TimeoutError.
    deadline = time.monotonic() + 30.0

    actual = client._next_message(deadline)

    # BUG: _next_message returned a list, violating the spec that says it
    # must return a dict conforming to JSON-RPC 2.0.
    if not isinstance(actual, dict):
        passed = True
        print(f"CONFIRMED — actual: {actual!r} (type: {type(actual).__name__}) | expected: dict conforming to JSON-RPC 2.0")
    else:
        print(f"NOT CONFIRMED — actual matched expected type: {actual!r}")

except ImportError as e:
    print(f"ERROR: Failed to import ElpClient: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    # Clean up the temporary workspace.
    import shutil
    try:
        shutil.rmtree(workspace, ignore_errors=True)
    except Exception:
        pass
```

### Probe Output

```
CONFIRMED — actual: [1, 2, 3] (type: list) | expected: dict conforming to JSON-RPC 2.0
```
