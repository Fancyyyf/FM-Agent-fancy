# Bug Report: request

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/request.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Sends a JSON-RPC 2.0 request to the LSP backend containing the given method,
    a params object (an empty dict when params is None), and a unique monotonically
    increasing integer request id
  - Returns the response result extracted from the backend's JSON-RPC response when
    the request succeeds before the deadline
  - When the backend returns a "content modified" error (signaling the document was
    modified during indexing), the identical request is retried to the same backend
    after a delay that grows exponentially with each retry attempt, bounded above
    by 5.0 seconds and by the remaining time before the deadline
  - Raises RuntimeError when the backend repeatedly returns "content modified" errors
    for all allowed retry attempts
  - Raises TimeoutError when self.timeout seconds of wall-clock time have elapsed
    since the call began without receiving a successful response, or when the
    remaining time before the deadline is exhausted before the next retry can begin

---

### Actual Behavior

After the call, let k be the number of attempts made (number of times _send was called). Then self._next_id = old self._next_id + k. Exactly k JSON-RPC request messages were sent, each with unique id from the range [old_id, old_id + k - 1], method 'method', and params equal to {} if the input params was None, else the given params. The deadline was deadline = time.monotonic() + self.timeout captured at start.

If the function returns a value result, then there exists an attempt index i (1 ≤ i ≤ _MAX_CONTENT_MODIFIED_RETRIES) with k = i such that:
- _wait_for_response(old_id + i - 1, deadline) returned result;
- for all j < i, _wait_for_response(old_id + j - 1, deadline) raised _ContentModifiedError, retries remained, remaining time > 0, and time.sleep(min(0.5*2**(j-1), 5.0, remaining)) was called;
- before the i-th attempt the deadline was not exceeded.

If RuntimeError is raised, then k = _MAX_CONTENT_MODIFIED_RETRIES and the last attempt (_MAX_CONTENT_MODIFIED_RETRIES-th) raised _ContentModifiedError, with no retries left. The message contains the method name.

If TimeoutError is raised, then there exists j (1 ≤ j < _MAX_CONTENT_MODIFIED_RETRIES) with k = j such that _wait_for_response(old_id + j - 1, deadline) raised _ContentModifiedError, and afterwards remaining = deadline - time.monotonic() ≤ 0. The message indicates timed out retrying the request.

If any other exception E is raised, then there exists i (1 ≤ i ≤ _MAX_CONTENT_MODIFIED_RETRIES) with k = i such that _wait_for_response(old_id + i - 1, deadline) raised E (E ≠ _ContentModifiedError), and the function propagates E.

The unreachable AssertionError is never raised.

---

## Code Evidence

Line 2:         actual_params = {} if params is None else params

(Corresponding to line 145 in `src/languages/erlang.py`)

---

## Trigger Condition

The specification requires that the request contains a params object (a dictionary) or, when params is None, an empty dict. The code does not enforce this; if a list (e.g., [1, 2, 3]) is passed as the params argument, the code sends that list as the JSON-RPC params array, violating the specification that a params object must be sent.

---

## How to trigger the bug

When `ElpClient.request()` is called with a list as the `params` argument, the code at line 145 (`actual_params = {} if params is None else params`) passes the list through as-is without validating that it is a dict. The list is then sent as the `params` field of the JSON-RPC request message, violating the spec requirement that `params` must always be an object (dict).

### Inputs

| Parameter | Value |
|-----------|-------|
| `method` | `"test/method"` |
| `params` | `[1, 2, 3]` (a list) |

### Expected (spec-correct) Output

The JSON-RPC request message should contain `"params": {}` (dict), or the function should reject/convert the non-dict `params` value.

### Actual (buggy) Output

The JSON-RPC request message contains `"params": [1, 2, 3]` (list), which violates the spec requiring a params object.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import ElpClient

client = ElpClient("/tmp")
client.timeout = 0.001

captured = []
def fake_send(message):
    captured.append(message)
client._send = fake_send

try:
    client.request("test/method", [1, 2, 3])
except Exception:
    pass

print(captured[0]["params"])  # actual (buggy) output: [1, 2, 3]
                               # expected (correct) output: dict (e.g., {})
```

---

## Probe Script

```py
"""Probe script for bug: request() sends list as JSON-RPC params array instead of object."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from languages import erlang
except ImportError as e:
    print(f"ERROR: Failed to import erlang module: {e}")
    sys.exit(1)


def main():
    # Create an ElpClient without starting an ELP subprocess
    # Set a tiny timeout so _wait_for_response fails fast
    client = erlang.ElpClient("/tmp")
    client.timeout = 0.001

    # Monkey-patch _send to capture the JSON-RPC message
    captured = []

    def fake_send(message):
        captured.append(message)

    client._send = fake_send

    # Call request() with a list as params — the spec says only dicts are allowed
    try:
        client.request("test/method", [1, 2, 3])
    except Exception:
        pass  # Expected — no ELP server running

    if not captured:
        print("ERROR: _send was never called")
        sys.exit(1)

    sent_params = captured[0].get("params")
    is_dict = isinstance(sent_params, dict)

    if is_dict:
        print(
            f"NOT CONFIRMED — params converted to dict: {sent_params!r}"
        )
    else:
        print(
            f"CONFIRMED — actual params type: {type(sent_params).__name__}, "
            f"value: {sent_params!r} | expected: dict"
        )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — actual params type: list, value: [1, 2, 3] | expected: dict
```
