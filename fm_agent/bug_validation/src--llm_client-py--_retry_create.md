# Bug Report: _retry_create

**Source file:** `src/llm_client-py/_retry_create.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a tuple of (response_text, usage_metadata_dict) from a successful LLM call
  - response_text is the text content returned by the LLM
  - usage_metadata_dict maps token-usage keys to numeric counts from the LLM response, or is an empty dict when no usage data is reported
  - When the CLI backend is active, the LLM interaction is delegated to an external agent
  - For direct client calls, Anthropic-family models use a dedicated native Anthropic endpoint; all other models use the standard chat-completions endpoint
  - Recoverable errors (rate limiting, server unavailability, and other transient HTTP/middleware failures) are retried with increasing delay bounded by a per-category maximum retry count
  - Non-recoverable errors (provider-rejected malformed requests) are propagated immediately without retry
  - Raises RuntimeError when a recoverable error exhausts its retry budget

---

### Actual Behavior

If `is_cli_backend_enabled()` is true, the function returns the result of `run_agent_for_messages(model, messages)` and does not raise any exception handled within this function. Otherwise, the function repeatedly attempts to obtain a completion for the given model and messages, retrying on rate-limit (HTTP 429 or RateLimitError) up to _MAX_RATE_LIMIT_RETRIES times with exponential backoff and on transient failures (HTTP 5xx, other exceptions) up to _MAX_LLM_RETRIES times with exponential backoff. If a completion is successful before retries are exhausted, the function returns a tuple (text, usage) where text is a string of the assistant's response content, and usage is a dictionary of token usage details (or an empty dict if no usage is available). If a BadRequestError or an HTTPError with status 400 occurs, the function raises that exception immediately. If rate-limit retries are exhausted, a RuntimeError is raised. If transient retries are exhausted, a RuntimeError is raised. Any other exception that occurs after the last allowed retry is wrapped in a RuntimeError. Formally, for every execution E of `_retry_create(client, model, messages)`: E either terminates with a return value R or raises exception X. (E returns R)  [(is_cli_backend_enabled()  R = run_agent_for_messages(model, messages))  (is_cli_backend_enabled()   t: str, u: dict . R = (t, u)  valid_response(t, u))]. (E raises X)  [X  {BadRequestError, HTTPError(400), RuntimeError}] where RuntimeError indicates either rate-limit or transient retry exhaustion. No other outcomes are possible, and the function respects the described retry limits and sleep intervals.

---

## Code Evidence

Line 60: except Exception as exc:

---

## Trigger Condition

The code catches all Exception instances and treats them as transient errors to retry. A TypeError caused by an invalid messages type is not a recoverable transient error; the specification requires that only recoverable errors (rate limiting, server unavailability, etc.) be retried. Non-recoverable errors like malformed input should be propagated immediately without retry, but the code retries them and eventually raises a RuntimeError.

---

## How to trigger the bug

The `except Exception as exc:` catch-all at line 237 (`src/llm_client.py` line 237) captures all Python exceptions — including non-recoverable client-side errors like `TypeError` — and treats them as transient failures worth retrying. According to the specification, only recoverable errors (rate limiting, server unavailability, HTTP 5xx, and similar transient HTTP/middleware failures) should be retried. Non-recoverable errors such as malformed input (e.g., passing a string instead of a list of dicts for `messages`) should propagate immediately.

Instead, the code retries the TypeError up to `_MAX_LLM_RETRIES` (5) times with exponential backoff, then wraps it in a `RuntimeError` — violating both the immediate-propagation requirement and the RuntimeError semantics (which should mean "retry budget exhausted on a genuinely recoverable error").

### Inputs

| Parameter | Value |
|-----------|-------|
| `client` | Mock OpenAI-compatible client whose `chat.completions.create()` raises `TypeError` |
| `model` | `"gpt-4o"` (non-Anthropic, triggers the OpenAI-compat path) |
| `messages` | `[{"role": "user", "content": "hi"}]` (valid format; the error is injected by the mock) |

### Expected (spec-correct) Output

`TypeError` raised immediately — no retries, no RuntimeError wrapping.

### Actual (buggy) Output

`RuntimeError("LLM request failed after 5 retries: invalid messages type: expected list of dicts, got str")` after 5 retries with exponential backoff.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from unittest.mock import patch

# Build mock client that raises TypeError on every create() call
class MockCreate:
    def __init__(self):
        self.call_count = 0
    def create(self, **kwargs):
        self.call_count += 1
        raise TypeError("invalid messages type")

mc = MockCreate()
mock_client = type('C', (), {'chat': type('C', (), {'completions': type('C', (), {'create': mc.create})()})()})()

with patch('src.llm_client.time.sleep', return_value=None):
    with patch('src.llm_client.is_cli_backend_enabled', return_value=False):
        with patch('src.llm_client._is_anthropic_model', return_value=False):
            from src.llm_client import _retry_create
            try:
                _retry_create(mock_client, "gpt-4o", [{"role": "user", "content": "hi"}])
            except RuntimeError as e:
                print(f"Bug: RuntimeError after {mc.call_count} calls — {e}")
# actual (buggy) output: RuntimeError after 5 calls
# expected (correct) output: TypeError raised immediately (1 call)
```

---

## Probe Script

```python
"""Probe for bug: _retry_create retries non-recoverable TypeError instead of propagating immediately.

Spec claim: non-recoverable errors (provider-rejected malformed requests) are
propagated immediately without retry. The code catches all Exception on line 237
and retries even non-recoverable errors like TypeError.
"""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot')

try:
    # -----------------------------------------------------------------------
    # Build a mock OpenAI-compatible client whose chat.completions.create
    # raises TypeError on every call. We count calls to detect retries.
    # -----------------------------------------------------------------------
    class MockCreate:
        def __init__(self):
            self.call_count = 0

        def create(self, **kwargs):
            self.call_count += 1
            raise TypeError("invalid messages type: expected list of dicts, got str")

    mock_create = MockCreate()
    mock_client = type('MockClient', (), {
        'chat': type('MockChat', (), {
            'completions': type('MockCompletions', (), {
                'create': mock_create.create,
            })(),
        })(),
    })()

    # -----------------------------------------------------------------------
    # Patch time.sleep (avoid multi-second waits), is_cli_backend_enabled
    # (must be False to exercise the retry branch), and _is_anthropic_model
    # (must be False to hit the OpenAI-compat path instead of Anthropic).
    # -----------------------------------------------------------------------
    patches = [
        patch('src.llm_client.time.sleep', return_value=None),
        patch('src.llm_client.is_cli_backend_enabled', return_value=False),
        patch('src.llm_client._is_anthropic_model', return_value=False),
    ]
    for p in patches:
        p.start()

    try:
        from src.llm_client import _retry_create, _MAX_LLM_RETRIES

        # Invoke _retry_create — using a non-anthropic model name and valid
        # messages so the only failure is the TypeError side_effect in our mock.
        _error_result = None
        try:
            _retry_create(mock_client, "gpt-4o", [{"role": "user", "content": "hi"}])
        except RuntimeError as e:
            _error_result = f"RuntimeError: {e}"
        except TypeError as e:
            _error_result = f"TypeError: {e}"
        except Exception as e:
            _error_result = f"{type(e).__name__}: {e}"

        call_count = mock_create.call_count

        # Bug is CONFIRMED if TypeError was retried (call_count > 1) instead
        # of propagating immediately. With _MAX_LLM_RETRIES=5, the buggy
        # behavior produces: 1 original call + 5 retries = 6 total.
        if call_count > 1:
            print(
                f"CONFIRMED — TypeError was retried ({call_count}x with "
                f"{_MAX_LLM_RETRIES} retry budget) instead of propagating "
                f"immediately; final result was {_error_result}"
            )
        else:
            print(
                f"NOT CONFIRMED — TypeError propagated immediately "
                f"({call_count} call, result: {_error_result})"
            )

    finally:
        for p in reversed(patches):
            p.stop()

except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
WARNING:root:LLM error (TypeError: invalid messages type: expected list of dicts, got str), sleeping 7.8s (attempt 1)
WARNING:root:LLM error (TypeError: invalid messages type: expected list of dicts, got str), sleeping 12.9s (attempt 2)
WARNING:root:LLM error (TypeError: invalid messages type: expected list of dicts, got str), sleeping 22.5s (attempt 3)
WARNING:root:LLM error (TypeError: invalid messages type: expected list of dicts, got str), sleeping 41.7s (attempt 4)
CONFIRMED — TypeError was retried (5x with 5 retry budget) instead of propagating immediately; final result was RuntimeError: LLM request failed after 5 retries: invalid messages type: expected list of dicts, got str
```
