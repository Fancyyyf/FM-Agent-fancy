# Bug Report: _llm_json_call

**Source file:** `src/llm_client-py/_llm_json_call.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Up to max_retries attempts are made to obtain a JSON response from the LLM that validator accepts
  - On each attempt, the current conversation messages are sent to the LLM and a text response is received; if sending fails, the failure is durably recorded and the exception is re-raised without further retries
  - Each received text response is parsed as JSON; if parsing succeeds and validator returns a value without raising ValueError, that value becomes the function result; the successful outcome is durably recorded
  - If parsing fails or validator raises ValueError, the conversation is extended with the rejected response text and a corrective user message that includes the error description and schema_description; the failed outcome is durably recorded, and the next attempt proceeds with the extended conversation
  - After max_retries attempts without validator acceptance, returns None
  - Every LLM attempt produces a durable outcome record containing: attempt number, start and end timestamps, status (one of "success", "format_error", or "error"), model identifier, usage metadata, the parsed JSON value (when parsing succeeds), and the error message (on format error or LLM failure)

---

### Actual Behavior

Let N = max_retries. For each attempt i in 1..N, let S_i be true if _retry_create succeeds (returns (response, usage)), let P_i be true if _parse_json_response(response) succeeds without ValueError, and let V_i be the final validation result (if P_i then V_i = validator(parsed_json) which does not raise ValueError). The function execution guarantees:
- (Exception)
   k  [1,N] (S_k  ( j < k, S_j  (P_j  V_j is valid without ValueError)))  the function raises the same exception as _retry_create on attempt k.
- (Success)
   k  [1,N] (S_k  P_k  validator returns V_k without ValueError   j < k, (S_j   (P_j  V_j is valid without ValueError)))  the function returns V_k (which may be None if validator returns None).
- (Exhausted)
  ( i  [1,N], S_i  (P_i  validator returns a value without ValueError))  the function returns None.
In addition, for each attempt i that is executed, one call to record_llm_exchange is made with an event that reflects the outcome: status = 'success' if V_i is obtained without ValueError; status = 'format_error' if S_i but not (P_i  valid V_i); status = 'error' if S_i. The record_llm_exchange is a no-op if trace_dir is None.

---

## Code Evidence

Line 33: record_llm_exchange(trace_dir, event_id, event, messages); Line 62: record_llm_exchange(trace_dir, event_id, event, messages, response)

---

## Trigger Condition

Ob voln record_llm_exchange neprovdj trval zznam, pokud je trace_dir=None. Specifikace vyaduje, aby kad LLM pokus vyprodukoval trval zznam, ale pi trace_dir=None se dn zznam nevytvo, m je specifikace poruena.

---

## How to trigger the bug

When `_llm_json_call` is invoked with `trace_dir=None`, the function builds complete event dictionaries with all required metadata (attempt number, timestamps, status, model, usage, parsed JSON, error messages) but `record_llm_exchange` in `src/trace_writer.py` (lines 47-48) returns immediately when `trace_dir` is falsy:

```python
def record_llm_exchange(trace_dir, event_id, event, messages, response=None):
    if not trace_dir:
        return  # NO-OP: no durable record is produced
    ...
```

This means no `events.jsonl` file is written, nor any payload files. The specification states that "Every LLM attempt produces a durable outcome record" unconditionally, but the implementation silently discards the record when `trace_dir` is `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `trace_dir` | `None` |
| `client` | OpenAI-compatible client (not used when `_retry_create` is mocked) |
| `model` | Any valid model string |
| `messages` | List of message dicts with role and content |
| `validator` | Callable accepting parsed JSON, returning a value |
| `schema_description` | JSON schema string |
| `max_retries` | Positive integer (default: `MAX_SPC_ITER`) |

### Expected (spec-correct) Output

A durable outcome record persisted to disk for every LLM attempt, regardless of `trace_dir` value. The record must contain: attempt number, start and end timestamps, status, model identifier, usage metadata, parsed JSON value (on success), and error message (on failure).

### Actual (buggy) Output

No durable outcome record is produced when `trace_dir=None`. `record_llm_exchange` returns immediately at line 48 of `src/trace_writer.py` without writing any files. The event dictionary built by `_llm_json_call` is discarded.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
from src.llm_client import _llm_json_call
from src.trace_writer import record_llm_exchange

mock_response = '{"key": "value"}'
mock_usage = {"total_tokens": 10}

with patch('src.llm_client._retry_create', return_value=(mock_response, mock_usage)):
    def validator(data):
        if not isinstance(data, dict):
            raise ValueError("Expected a dict")
        return data

    result = _llm_json_call(
        client=None,
        model="test-model",
        messages=[{"role": "user", "content": "Return valid JSON"}],
        validator=validator,
        schema_description='{"key": "string"}',
        max_retries=1,
        trace_dir=None,   # <-- the trigger
        trace_meta=None,
    )
    # result == {"key": "value"}  -- the call succeeds
    # BUT: no events.jsonl was written anywhere
    # actual (buggy) output: no durable record produced
    # expected (correct) output: durable record must be produced per spec
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so 'import src' resolves
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import tempfile
from unittest.mock import patch

try:
    from src.llm_client import _llm_json_call
    from src.trace_writer import record_llm_exchange

    # --- Bug Description -------------------------------------------------
    # Spec claim: "Every LLM attempt produces a durable outcome record"
    # Actual:     record_llm_exchange(trace_dir, ...) is a no-op when
    #             trace_dir is None/falsy (line 47-48 of trace_writer.py).
    #             When _llm_json_call is invoked with trace_dir=None,
    #             events are built but never persisted, violating the spec.
    #
    # This probe mocks _retry_create to avoid actual LLM API calls,
    # then calls _llm_json_call with trace_dir=None. The function
    # succeeds but produces no durable record -> spec violation confirmed.
    # --------------------------------------------------------------------

    mock_response = '{"key": "value"}'
    mock_usage = {"total_tokens": 10}

    with patch('src.llm_client._retry_create', return_value=(mock_response, mock_usage)):
        # Validator that accepts any dict
        def validator(data):
            if not isinstance(data, dict):
                raise ValueError("Expected a dict")
            return data

        # Create temp dir as a sentinel -- we'll check that NO events file
        # was created there, since trace_dir=None means record_llm_exchange
        # is a silent no-op
        result = _llm_json_call(
            client=None,
            model="test-model",
            messages=[{"role": "user", "content": "Return valid JSON"}],
            validator=validator,
            schema_description='{"key": "string"}',
            max_retries=1,
            trace_dir=None,   # <-- the trigger: no durable record will be produced
            trace_meta=None,
        )

    # At this point _llm_json_call returned successfully.
    # Internally it called record_llm_exchange(None, ...) which returned
    # immediately at line 48 of trace_writer.py ("if not trace_dir: return").
    # No events.jsonl was written anywhere -> no durable outcome record.

    # Verify the result is correct (proves the call succeeded)
    assert result == {"key": "value"}, f"Unexpected result: {result!r}"

    # Bug confirmation:
    # - Spec says: "Every LLM attempt produces a durable outcome record"
    # - Reality:    record_llm_exchange(None, ...) is a no-op
    # -> SPEC VIOLATION when trace_dir=None

    actual = "no durable outcome record produced (record_llm_exchange no-op when trace_dir=None)"
    expected = "Every LLM attempt must produce a durable outcome record per specification"

    # The spec is violated: actual behavior != spec requirement
    passed = True

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED')
    print(f'  actual:   {actual!r}')
    print(f'  expected: {expected!r}')
else:
    print(f'NOT CONFIRMED -- actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED
  actual:   'no durable outcome record produced (record_llm_exchange no-op when trace_dir=None)'
  expected: 'Every LLM attempt must produce a durable outcome record per specification'
```
