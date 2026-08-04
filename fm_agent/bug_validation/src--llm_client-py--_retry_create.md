# Bug Report: _retry_create

**Source file:** `src/llm_client.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a 2-tuple (text, usage) where text is a non-empty string containing the LLM assistant response content and usage is a dict representing the token-usage metadata from the API response (an empty dict when no usage data is present in the response). On failure, raises an exception with the following error contract: (a) non-recoverable errors — HTTP 400 responses and their SDK-equivalent exception types — are raised immediately without any retry; (b) rate-limiting errors — HTTP 429 responses and their SDK-equivalent exception types — are retried with exponential backoff plus random jitter, bounded above and subject to a maximum retry count; upon exhausting the rate-limit retry budget, a RuntimeError is raised; (c) transient server errors — HTTP 5xx responses — and other unexpected exception types are retried with exponential backoff plus random jitter, subject to a distinct maximum retry count; upon exhausting the transient-error retry budget, a RuntimeError is raised. The backoff wait duration for each error category grows exponentially with each successive attempt and is clamped at a category-specific upper bound. When a CLI-based LLM backend is active, the request is delegated to the CLI agent subprocess and its return value is returned directly without further processing. When the model is identified as belonging to the Anthropic model family, the request is routed to the native Anthropic API endpoint rather than the OpenAI-compatible endpoint.

---

### Actual Behavior

If `is_cli_backend_enabled()` evaluates to True, the function delegates to `run_agent_for_messages(model, messages)` and either returns its result — a 2tuple `(text, usage_dict)` where `text` is a string and `usage_dict` is a dict (possibly empty) — or propagates any exception raised by that call. Otherwise, the function enters a retry loop. In each iteration:
- If the model is detected as an Anthropic model (`_is_anthropic_model(model)` is True), it calls `_anthropic_create(model, messages)`. For nonAnthropic models, it calls `client.chat.completions.create(model=model, messages=messages, **extra)` (with `extra` possibly containing an `extra_body` if URL injection is enabled).
- On a successful call, the response content from the first choice (`response.choices[0].message.content`) becomes `text`; if `response.usage` is not None, `usage_dict` is obtained via `response.usage.model_dump()`, otherwise `usage_dict` is an empty dict. The tuple `(text, usage_dict)` is returned.
- If `BadRequestError` is raised (by the API or client), it is immediately reraised without retry.
- If `urllib.error.HTTPError` is raised:
   * If `exc.code == 400`, reraise the exception.
   * If `exc.code == 429`, increment a ratelimit attempt counter. If the counter reaches `_MAX_RATE_LIMIT_RETRIES`, raise `RuntimeError` with a descriptive message and the original exception as cause. Otherwise wait for `min(2 ** (attempts-1) * 5, 300) + random.uniform(1, 10)` seconds and continue.
   * For all other status codes (e.g., 5xx), increment a transient failure attempt counter. If that counter reaches `_MAX_LLM_RETRIES`, raise `RuntimeError` with a descriptive message and the original exception as cause. Otherwise wait for `min(2 ** (attempts-1) * 5, 60) + random.uniform(1, 3)` seconds and continue.
- If `RateLimitError` is raised, apply the same logic as for HTTP 429 (increment the ratelimit counter, possibly raise `RuntimeError` after retries exhausted, else wait with exponential backoff plus jitter).
- For all other `Exception` types, apply the transient-failure retry logic: increment counter, possibly raise `RuntimeError`, else wait with exponential backoff plus jitter and continue.

---

## Code Evidence

Line 198: `text = response.choices[0].message.content`
Line 200: `return text, usage`

These lines in `src/llm_client.py` extract the response text from the API and return it with no check for emptiness. The content is passed through directly — if the API responds with `content=""`, the function returns `("", {})` to the caller.

---

## Trigger Condition

The specification requires the returned text to be a non-empty string. The code does not verify that the content is non-empty; it returns whatever the API provides. When the API responds with an empty string (e.g., `content=''`), the code returns an empty text, which violates the post-condition.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `client` | Mock OpenAI client returning `choices[0].message.content = ""` |
| `model` | `"gpt-4"` |
| `messages` | `[{"role": "user", "content": "hello"}]` |

### Expected (spec-correct) Output

`("non-empty string", {})` — the function must return a non-empty text string per the specification.

### Actual (buggy) Output

`("", {})` — the function returns an empty string because it does not validate the content.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_API_BASE_URL", "https://api.example.com/v1")
from unittest.mock import MagicMock, patch
from src.llm_client import _retry_create

client = MagicMock()
choice = MagicMock()
choice.message.content = ""   # empty content triggers the bug
resp = MagicMock()
resp.choices = [choice]
resp.usage = None
client.chat.completions.create.return_value = resp

with patch("src.llm_client.is_cli_backend_enabled", return_value=False), \
     patch("src.llm_client._is_anthropic_model", return_value=False):
    text, usage = _retry_create(client, "gpt-4", [{"role": "user", "content": "hello"}])

# actual (buggy) output: text = ""
# expected (correct) output: text should be non-empty
```

---

## Probe Script

```python
"""Probe for bug: _retry_create returns empty text when API responds with empty content.

Spec claim: Returns a 2-tuple (text, usage) where text is a non-empty string.
Actual: The code does not verify content is non-empty — returns whatever the API provides.
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Allow importing the src package from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Ensure config loads without a real .env / key
os.environ.setdefault("LLM_API_KEY", "test-mock-key")
os.environ.setdefault("LLM_API_BASE_URL", "https://api.example.com/v1")

try:
    from src.llm_client import _retry_create
except Exception as e:
    print(f"ERROR: Failed to import: {e}")
    sys.exit(1)

# Build a mock OpenAI client whose chat.completions.create returns empty content.
mock_client = MagicMock()
mock_choice = MagicMock()
mock_choice.message.content = ""  # empty — this is the trigger condition
mock_response = MagicMock()
mock_response.choices = [mock_choice]
mock_response.usage = None  # no usage data → usage_dict should be {}

mock_client.chat.completions.create.return_value = mock_response

try:
    # Patch is_cli_backend_enabled and _is_anthropic_model to ensure we hit the
    # OpenAI-compat code path (non-CLI, non-Anthropic).
    with (
        patch("src.llm_client.is_cli_backend_enabled", return_value=False),
        patch("src.llm_client._is_anthropic_model", return_value=False),
    ):
        text, usage = _retry_create(mock_client, "gpt-4", [{"role": "user", "content": "hello"}])
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# The spec requires text to be a non-empty string.
# The buggy code returns "" — the post-condition is violated.
expected = "non-empty string (spec requirement)"
passed = text == ""  # True → bug reproduced because text should NOT be empty

if passed:
    print(f"CONFIRMED — actual: {text!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matches expected: {text!r}")
```

### Probe Output

```
CONFIRMED — actual: '' | expected: 'non-empty string (spec requirement)'
```
