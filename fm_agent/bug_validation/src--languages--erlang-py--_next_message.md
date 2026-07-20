# Bug Report: ElpClient._next_message

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_next_message.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Blocks until a message is available from self._messages and returns that message,
    provided the message is not an instance of BaseException
  - Raises TimeoutError when the wall-clock monotonic time reaches or exceeds deadline
    before a message becomes available
  - Raises RuntimeError when the received message is an instance of BaseException

---

### Actual Behavior

After execution, one of three outcomes holds:\n1. (Normal return) The method returns a value `m` that is not an instance of BaseException; `m` was the head of `self._messages` before the call, and `self._messages` now lacks that head element; `time.monotonic() <= deadline`.\n2. (TimeoutError raised) A `TimeoutError` is raised, `time.monotonic() >= deadline`, and `self._messages` is unchanged (no element removed).\n3. (RuntimeError raised) A `RuntimeError` chained from an item `e` is raised; `e` was the head of `self._messages` before the call and is an instance of BaseException; `self._messages` now lacks `e`; `time.monotonic() < deadline`.\nFormally, let `Q` be the pre-state value of `self._messages`, `Q'` the post-state value, and `t` be `time.monotonic()` after the call. Then:\n( RETURN m    m  BaseException    Q = [m] ++ Q'    t  deadline ) \n( RAISES TimeoutError    t  deadline    Q = Q' ) \n( RAISES RuntimeError with __cause__ e    isinstance(e, BaseException)    Q = [e] ++ Q'    t < deadline )

---

## Code Evidence

```
Line 3: if remaining <= 0:
Line 4: raise TimeoutError("timed out waiting for ELP")
```

---

## Trigger Condition

The code raises TimeoutError immediately whenever remaining <= 0, without attempting to retrieve a message from self._messages. When remaining == 0 and a message is already in the queue, the specification requires returning that message (or raising RuntimeError if it is a BaseException), because the deadline is reached exactly when the message is available, not before. The code's early return/cutoff violates the semantics of a zero-timeout non-blocking attempt.

---

## How to trigger the bug

The `_next_message` method checks `remaining = deadline - time.monotonic()` and immediately raises `TimeoutError` when `remaining <= 0`, without checking `self._messages` for an already-available message. When a message is in the queue and `deadline` equals (or is very close to) the current monotonic time, the specification requires returning that message, but the buggy code raises `TimeoutError`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `self._messages` contents | `{"jsonrpc": "2.0", "id": 1, "result": "hello"}` |
| `deadline` | `time.monotonic()` (current monotonic time → remaining ≤ 0) |

### Expected (spec-correct) Output

`{"jsonrpc": "2.0", "id": 1, "result": "hello"}` (the queued message)

### Actual (buggy) Output

`TimeoutError("timed out waiting for ELP")` is raised

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import ElpClient
import queue, time, tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    client = ElpClient(tmpdir)
    client._messages.put({"jsonrpc": "2.0", "id": 1, "result": "hello"})
    deadline = time.monotonic()  # remaining == 0
    result = client._next_message(deadline)  # raises TimeoutError
# actual (buggy) output: TimeoutError raised
# expected (correct) output: {"jsonrpc": "2.0", "id": 1, "result": "hello"}
```

---

## Probe Script

```python
import sys
import os
import queue
import time

# Ensure the repo root is on sys.path so 'src.languages.erlang' resolves.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.erlang import ElpClient

    # Create an ElpClient instance with a temporary proj_dir. We never start
    # a subprocess, so the internal state is all we need for the test.
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        client = ElpClient(tmpdir)

        # Place a message in the queue BEFORE calling _next_message, simulating
        # a message that arrived ahead of the deadline check.
        test_message = {"jsonrpc": "2.0", "id": 1, "result": "hello"}
        client._messages.put(test_message)

        # deadline = current monotonic time → remaining <= 0
        deadline = time.monotonic()
        expected = test_message

        try:
            actual = client._next_message(deadline)
        except TimeoutError:
            actual = TimeoutError  # sentinel for "TimeoutError was raised"

        # Bug reproduced if TimeoutError was raised despite a queued message
        passed = actual is TimeoutError

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: TimeoutError raised | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: TimeoutError raised | expected: {'jsonrpc': '2.0', 'id': 1, 'result': 'hello'}
```
