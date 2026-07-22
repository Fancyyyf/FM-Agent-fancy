# Bug Report: ElpClient.request

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Transmits a JSON-RPC 2.0 request to the server with the given method
    and params (where None params is treated as an empty object), tagged
    with a unique integer identifier that is strictly increasing across
    successive calls on the same client instance
  - Blocks the caller until the server returns a response matching that
    identifier or until the total elapsed time since entry reaches
    self.timeout seconds, whichever occurs first
  - On success: returns the value of the "result" field from the matching
    response
  - When the server indicates a transient ContentModified error: re-issues
    the request up to a fixed maximum number of total attempts, bounded in
    total duration by self.timeout seconds from entry; when all attempts
    are exhausted without success, raises RuntimeError identifying the
    failing method
  - When no matching response arrives before self.timeout seconds elapse
    from entry: raises TimeoutError
  - When the server responds with an error whose semantics are not covered
    by the retry policy: raises RuntimeError

---

### Actual Behavior

After execution, if _MAX_CONTENT_MODIFIED_RETRIES > 0, exactly one of the following outcomes occurs: (i) The method returns a value V such that V equals the 'result' field of the JSON-RPC response with matching request id, and no transient content-modified error was raised on the final attempt. (ii) A TimeoutError is raised, because either a _wait_for_response call timed out (deadline exceeded or channel closed) on any attempt, or the deadline expired during retry handling after catching a _ContentModifiedError. (iii) A RuntimeError is raised, either because a non-transient server error was received on any attempt (from _wait_for_response), or because all _MAX_CONTENT_MODIFIED_RETRIES attempts resulted in transient content-modified errors and the retry limit was reached. (iv) Any other exception raised by _send or _wait_for_response (e.g., connection errors) propagates without being caught. If _MAX_CONTENT_MODIFIED_RETRIES ≤ 0, an AssertionError with message 'unreachable' is raised. Formally: (∃ v. return v ∧ response_of_final_attempt.result = v ∧ no _ContentModifiedError on final attempt) ∨ (raise TimeoutError ∧ (∃ attempt. _wait_for_response raised TimeoutError on attempt ∨ (caught _ContentModifiedError ∧ deadline − time.monotonic() ≤ 0))) ∨ (raise RuntimeError ∧ ((∃ attempt. _wait_for_response raised RuntimeError not subclass of _ContentModifiedError) ∨ (∀ attempts. _ContentModifiedError raised))) ∨ (raise AssertionError ∧ _MAX_CONTENT_MODIFIED_RETRIES ≤ 0). The communication channel state remains open under normal returns; on exception its state is undefined.

---

## Code Evidence

Line 4:     for attempt in range(_MAX_CONTENT_MODIFIED_RETRIES):
Line 26:         raise AssertionError("unreachable")

---

## Trigger Condition

The specification only permits returning a result, raising TimeoutError, or raising RuntimeError. When _MAX_CONTENT_MODIFIED_RETRIES ≤ 0, the code raises an AssertionError, which is not among the allowed outcomes.

---

## How to trigger the bug

When `_MAX_CONTENT_MODIFIED_RETRIES` is set to 0 (or any non-positive value), the `for` loop `for attempt in range(_MAX_CONTENT_MODIFIED_RETRIES)` produces zero iterations, causing execution to fall through the loop body entirely and reach the `raise AssertionError("unreachable")` statement. This raises an `AssertionError` — an exception type not accounted for in the specification, which only allows returning a result, raising `TimeoutError`, or raising `RuntimeError`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `_MAX_CONTENT_MODIFIED_RETRIES` (module constant, monkey-patched) | `0` |
| `method` | `"test_method"` |
| `params` | `{"key": "value"}` |
| `self.timeout` | `5.0` |

### Expected (spec-correct) Output

Should raise `TimeoutError` (because with zero retries, there is no response) or `RuntimeError` (because the retry budget is exhausted), but **not** `AssertionError`.

### Actual (buggy) Output

`AssertionError` with message `"unreachable"` is raised.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import src.languages.erlang as erlang_module

original = erlang_module._MAX_CONTENT_MODIFIED_RETRIES
erlang_module._MAX_CONTENT_MODIFIED_RETRIES = 0

client = erlang_module.ElpClient("/tmp")
client.timeout = 5.0

try:
    client.request("test_method", {"key": "value"})
except AssertionError as e:
    print(f"BUG: {e}")  # AssertionError: unreachable
finally:
    erlang_module._MAX_CONTENT_MODIFIED_RETRIES = original
// actual (buggy) output: AssertionError('unreachable')
// expected (correct) output: TimeoutError or RuntimeError
```

---

## Probe Script

```python
"""Probe for ElpClient::request -- _MAX_CONTENT_MODIFIED_RETRIES=0 triggers AssertionError not in spec."""

import os
import sys
import tempfile

# Add repo root to path so the entry-point import works
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

# --- Create a temporary workspace for this probe (per FM-Agent guard) ---
tmpdir = tempfile.mkdtemp(prefix="probe_ElpClient_request_")
os.chdir(tmpdir)

try:
    import src.languages.erlang as erlang_module

    # Monkey-patch the retry constant to zero to trigger the unreachable path
    original_retries = erlang_module._MAX_CONTENT_MODIFIED_RETRIES
    erlang_module._MAX_CONTENT_MODIFIED_RETRIES = 0

    # Instantiate ElpClient without __enter__ (no subprocess spawned)
    client = erlang_module.ElpClient("/tmp")
    client.timeout = 5.0

    try:
        result = client.request("test_method", {"key": "value"})
        print(f"NOT CONFIRMED — method returned result: {result!r}")
    except AssertionError as e:
        print(f"CONFIRMED — AssertionError raised (spec violation): {e}")
    except TimeoutError:
        print("NOT CONFIRMED — TimeoutError raised (spec-compliant)")
    except RuntimeError:
        print("NOT CONFIRMED — RuntimeError raised (spec-compliant)")
    except Exception as e:
        print(f"CONFIRMED — unexpected exception type {type(e).__name__}: {e}")
    finally:
        erlang_module._MAX_CONTENT_MODIFIED_RETRIES = original_retries

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — AssertionError raised (spec violation): unreachable
```
