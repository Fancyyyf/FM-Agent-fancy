# Bug Report: ElpClient::request

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/languages/erlang-py/ElpClient::request.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Sends a JSON-RPC 2.0 request with the given method and params to the ELP server. When params is None, an empty dict is used in its place. Returns the 'result' field of the server's JSON-RPC response, parsed to the appropriate Python type. Transparently retries on transient server-side content-modification errors with exponential backoff bounded by the instance's configured message-processing timeout. Raises RuntimeError when all retries are exhausted on a content-modification error. Raises TimeoutError when the overall message-processing deadline expires before a response is received. Raises an exception when the server is unreachable, the server returns a non-retriable JSON-RPC error response, or the connection is lost.

---

### Actual Behavior

After the method 'request' executes, the following post-conditions hold based on the outcome:

- If the method returns a value v:
  A JSON-RPC 2.0 request with a unique integer id (equal to self._next_id at the start of the attempt) was sent, and before the deadline the server responded with a non-ContentModifiedError success response matching that id, with 'result' v. The method may have retried after receiving ContentModifiedError responses, each time sending a new request with incremented id. The returned v is the result from the first attempt where no ContentModifiedError occurred. The connection remains active.
  Formal: ∃ i ∈ [0, _MAX_CONTENT_MODIFIED_RETRIES) such that (∀ j < i, attempt j received ContentModifiedError) ∧ (attempt i received success with result v) ∧ (time_monotonic() ≤ deadline at response) ∧ (connection active).

- If the method raises RuntimeError:
  All _MAX_CONTENT_MODIFIED_RETRIES attempts received ContentModifiedError, and the deadline was not exceeded before the final attempt's error catch. No successful response was returned.
  Formal: (∀ i ∈ [0, _MAX_CONTENT_MODIFIED_RETRIES), attempt i received ContentModifiedError) ∧ (deadline - time_monotonic() after final ContentModifiedError > 0 but retries exhausted).

- If the method raises TimeoutError:
  Either (a) a _wait_for_response call raised TimeoutError because the deadline was reached without a response for the sent id, or (b) after a ContentModifiedError, the remaining time (deadline - time_monotonic()) was ≤ 0, causing an explicit TimeoutError. In both cases, no successful response was obtained.
  Formal: ∃ i ∈ [0, _MAX_CONTENT_MODIFIED_RETRIES) such that ( (∀ j < i, attempt j received ContentModifiedError) ∧ ( (attempt i raised TimeoutError during _wait_for_response) ∨ (attempt i received ContentModifiedError ∧ deadline - time_monotonic() ≤ 0) ) ).

- If any other exception propagates:
  An exception from _send (e.g., connection failure) or from _wait_for_response (non-ContentModifiedError JSON-RPC error) propagated out without a ContentModifiedError retry loop. The connection state is undefined after such an exception.

---

## Code Evidence

Line 18:                 if attempt + 1 == _MAX_CONTENT_MODIFIED_RETRIES:
Line 19:                     raise RuntimeError(
Line 20:                         f"ELP request {method} repeatedly failed: {exc.error}"
Line 21:                     ) from exc

---

## Trigger Condition

When the last retry receives a ContentModifiedError after the overall deadline has expired, the code immediately raises RuntimeError without checking the remaining time. The specification requires TimeoutError when the deadline expires before a response is received, which should take precedence over RuntimeError.

---

## How to trigger the bug

The `ElpClient.request()` method iterates up to `_MAX_CONTENT_MODIFIED_RETRIES` (5) times. On each attempt, it sends a JSON-RPC request and waits for a response. If the server returns a `ContentModifiedError`, the method catches the exception and either retries or re-raises.

The bug is on the **last attempt** (line 18-21): when `attempt + 1 == _MAX_CONTENT_MODIFIED_RETRIES`, the code unconditionally raises `RuntimeError` **without first checking whether the deadline has expired**. By contrast, on earlier attempts (lines 22-24), the code does check `remaining = deadline - time.monotonic()` and raises `TimeoutError` when `remaining <= 0`.

Per the specification, `TimeoutError` must be raised whenever the overall message-processing deadline expires before a response is received. The deadline-expiration check should take precedence over the retries-exhausted check.

### Inputs

| Parameter | Value |
|-----------|-------|
| `method` | `"test/method"` |
| `params` | `{"key": "value"}` |
| `self.timeout` | `10` seconds |
| `self._wait_for_response` | Always raises `_ContentModifiedError` (code -32801) |
| Mocks | `time.monotonic()` returns `[0.0, 5.0, 6.0, 7.0, 8.0, 11.0]`; `time.sleep` is a no-op |

### Expected (spec-correct) Output

The code should raise `TimeoutError` because by the fifth (last) attempt, `time.monotonic()` has reached `11.0`, which exceeds the `deadline` of `10.0`. The specification mandates that `TimeoutError` takes precedence when the deadline expires.

### Actual (buggy) Output

The code raises `RuntimeError("ELP request test/method repeatedly failed: ...")` because lines 18-21 unconditionally raise `RuntimeError` on the last attempt without checking `remaining = deadline - time.monotonic()`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import time
from unittest.mock import patch, MagicMock
from src.languages.erlang import ElpClient, _ContentModifiedError

client = object.__new__(ElpClient)
client._messages = MagicMock()
client._write_lock = MagicMock()
client._proc = MagicMock()
client._proc.stdin = MagicMock()
client._next_id = 1
client.timeout = 10

client._send = MagicMock()
content_error = _ContentModifiedError({"code": -32801, "message": "content modified"})
client._wait_for_response = MagicMock(side_effect=content_error)

monotonic_values = [0.0, 5.0, 6.0, 7.0, 8.0, 11.0]
idx = [0]
def mock_monotonic():
    val = monotonic_values[min(idx[0], len(monotonic_values)-1)]
    idx[0] += 1
    return val

with patch("src.languages.erlang.time.monotonic", mock_monotonic), \
     patch("src.languages.erlang.time.sleep", MagicMock()):
    client.request("test/method", {"key": "value"})
# actual (buggy) output: RuntimeError raised
# expected (correct) output: TimeoutError raised
```

---

## Probe Script

```python
"""Probe script for bug: src--languages--erlang-py--ElpClient::request

Bug: ElpClient.request() raises RuntimeError instead of TimeoutError when the
last retry receives ContentModifiedError after the overall deadline has expired.
The spec requires TimeoutError to take precedence over RuntimeError.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the repo root is on sys.path so 'src.languages.erlang' is importable.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.languages.erlang import ElpClient, _ContentModifiedError, _MAX_CONTENT_MODIFIED_RETRIES


try:
    # ------------------------------------------------------------------
    # Build a mock ElpClient that bypasses real __init__ (no subprocess).
    # ------------------------------------------------------------------
    client = object.__new__(ElpClient)
    client._messages = MagicMock()
    client._write_lock = MagicMock()
    client._proc = MagicMock()
    client._proc.stdin = MagicMock()
    client._next_id = 1
    client.timeout = 10  # deadline = monotonic(0) + 10.0 = 10.0

    # _send is a no-op; we only care about control flow after the error.
    client._send = MagicMock()

    # _wait_for_response always signals a content-modified error so every
    # attempt fails.
    content_error = _ContentModifiedError({"code": -32801, "message": "content modified"})
    client._wait_for_response = MagicMock(side_effect=content_error)

    # ------------------------------------------------------------------
    # Control time.monotonic() so that:
    #   - deadline = 0 + 10 = 10
    #   - attempts 0-3 see remaining > 0  → sleep and retry
    #   - by attempt 4 (the 5th), monotonic ≥ 11  →  deadline expired
    # ------------------------------------------------------------------
    monotonic_values = [0.0, 5.0, 6.0, 7.0, 8.0, 11.0]
    monotonic_idx = [0]

    def mock_monotonic():
        idx = min(monotonic_idx[0], len(monotonic_values) - 1)
        value = monotonic_values[idx]
        monotonic_idx[0] += 1
        return value

    # ------------------------------------------------------------------
    # Run the request and capture which exception type propagates.
    # ------------------------------------------------------------------
    actual_type = None
    with patch("src.languages.erlang.time.monotonic", mock_monotonic), \
         patch("src.languages.erlang.time.sleep", MagicMock()):
        try:
            client.request("test/method", {"key": "value"})
        except RuntimeError:
            actual_type = RuntimeError
        except TimeoutError:
            actual_type = TimeoutError
        except Exception as e:
            actual_type = type(e)

    # Spec says TimeoutError should win when the deadline has expired.
    # The code raises RuntimeError (bug) because it skips the remaining check
    # on the last attempt.
    expected_type = TimeoutError
    bug_reproduced = actual_type != expected_type

    if bug_reproduced:
        print(
            f"CONFIRMED — actual: {actual_type.__name__} raised "
            f"| expected: TimeoutError | deadline=10.0, "
            f"monotonic_reached={monotonic_values[-1]}, deadline expired on final retry"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual_type.__name__}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: RuntimeError raised | expected: TimeoutError | deadline=10.0, monotonic_reached=11.0, deadline expired on final retry
```
