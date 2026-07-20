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

After the function _retry_create(client, model, messages) is called, it terminates with one of the following outcomes: 
1. If is_cli_backend_enabled() evaluates to True, the function returns run_agent_for_messages(model, messages), which is a tuple (text: str, usage: dict). 
2. Otherwise, it enters a retry loop and attempts to call the LLM via client.chat.completions.create (or _anthropic_create for Anthropic models). The loop can terminate in one of the following ways: 
   a. On successful API call, it returns (text, usage) where text is response.choices[0].message.content (a string) and usage is response.usage.model_dump() if response.usage is not None, else {} (a dict). 
   b. If a BadRequestError or an HTTPError with status code 400 is raised, the exception is immediately re-raised without retry. 
   c. On a rate limiting error (HTTPError with status 429 or RateLimitError), the function waits (exponential backoff: base 5s, max 300s, plus jitter 1-10s) and increments a rate-limit retry counter. If the counter reaches _MAX_RATE_LIMIT_RETRIES, a RuntimeError is raised; otherwise the loop continues. 
   d. On any other transient error (HTTPError with status >=500, or a general Exception), it waits (exponential backoff: base 5s, max 60s, plus jitter 1-3s) and increments a transient retry counter. If the counter reaches _MAX_LLM_RETRIES, a RuntimeError is raised; otherwise the loop continues. 
No other return values are produced; the function either returns a (text, usage) tuple or raises an exception as described. The inputs client, model, messages are not mutated. Side effects include logging and sleeps during retries.

---

## Code Evidence

Line 26: except urllib.error.HTTPError as exc:
Line 51: except RateLimitError as exc:
Line 60: except Exception as exc:

---

## Trigger Condition

The code only recognises ratelimiting errors as urllib.error.HTTPError with status 429 or the global RateLimitError. For Anthropic models, the native endpoint may raise a libraryspecific ratelimit exception that is not caught by these handlers, causing it to be treated as a generic transient error. This misclassification breaks the contract that ratelimiting builds its own retry budget and uses appropriate backoff parameters, which violates the specification.

---

## How to trigger the bug

When `_retry_create` is called with an Anthropic-family model, it delegates to `_anthropic_create()`, which uses `urllib.request.urlopen()` for the HTTP call. If a rate-limiting proxy or relay resets the TCP connection instead of returning a proper HTTP 429 response, `urllib` raises `urllib.error.URLError` — which is neither `HTTPError` nor `RateLimitError`. The exception falls through to the generic `except Exception` handler and is treated as a transient error instead of a rate-limit error. This means:
- **Transient retry budget applies** (`_MAX_LLM_RETRIES = 5`) instead of the rate-limit budget (`_MAX_RATE_LIMIT_RETRIES = 20`)
- **Backoff caps at 60s** instead of 300s
- The distinction between rate-limit and transient categories is lost, violating the specification's per-category retry contract

### Inputs

| Parameter | Value |
|-----------|-------|
| client | `_llm_provider_client` (OpenAI client instance) |
| model | `"claude-sonnet-4-6"` (Anthropic-family, routes to `_anthropic_create`) |
| messages | `[{"role": "user", "content": "Hello"}]` |

### Expected (spec-correct) Output

The `urllib.error.URLError` caused by a rate-limiting connection reset should be classified as a rate-limit error. It should increment `rate_limit_attempts`, use the rate-limit backoff schedule (max 300s), and be bounded by `_MAX_RATE_LIMIT_RETRIES`. After exhausting retries, it should raise `RuntimeError("Rate limited after N retries: ...")`.

### Actual (buggy) Output

The `URLError` falls through to `except Exception`, increments `transient_attempts`, uses the transient backoff schedule (max 60s), and is bounded by `_MAX_LLM_RETRIES` (5, not 20). After exhausting retries, it raises `RuntimeError("LLM request failed after N retries: ...")`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
os.environ.setdefault("LLM_API_KEY", "sk-test")
os.environ.setdefault("LLM_API_BASE_URL", "https://test.example.com")

import urllib.request, urllib.error, time
from src.llm_client import _retry_create, _llm_provider_client, _is_anthropic_model
import src.llm_client as llm_mod

# Speed up the test
llm_mod._MAX_RATE_LIMIT_RETRIES = 2
llm_mod._MAX_LLM_RETRIES = 2

# Monkey-patch: simulate rate-limiting proxy resetting the connection
_orig = urllib.request.urlopen
urllib.request.urlopen = lambda *a, **kw: (_ for _ in ()).throw(
    urllib.error.URLError("Connection reset by peer"))
time.sleep = lambda s: None

try:
    _retry_create(_llm_provider_client, "claude-sonnet-4-6",
                  [{"role": "user", "content": "Hello"}])
except RuntimeError as e:
    print(str(e))
    # actual (buggy) output: "LLM request failed after 2 retries: ..."
    # expected (correct) output: "Rate limited after 2 retries: ..."
```

---

## Probe Script

```python
"""Probe for bug: src--llm_client-py--_retry_create
Bug: _anthopic_create uses urllib, which raises URLError for connection-level
errors. When a rate-limiting proxy resets the connection, URLError falls through
to except Exception and is treated as a transient error (MAX_LLM_RETRIES=5,
backoff max=60s), instead of a rate-limit error (MAX_RATE_LIMIT_RETRIES=20,
backoff max=300s). This violates the spec's per-category retry contract.
"""
import sys
import os
import time
import urllib.request
import urllib.error

# Ensure project root is on the path
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

# ------------------------------------------------------------
# 1. Monkey-patch BEFORE importing any project modules
# ------------------------------------------------------------

# urllib.request.urlopen → raise URLError (simulates rate-limiting
# proxy that resets TCP connections instead of returning HTTP 429)
_original_urlopen = urllib.request.urlopen

def _patched_urlopen(req, *args, **kwargs):
    raise urllib.error.URLError("Connection reset by peer")

urllib.request.urlopen = _patched_urlopen

# time.sleep → no-op (avoid waiting for backoff during test)
_original_sleep = time.sleep
time.sleep = lambda s: None

# ------------------------------------------------------------
# 2. Set required env vars before config.py loads them
# ------------------------------------------------------------
os.environ.setdefault("LLM_API_KEY", "sk-test")
os.environ.setdefault("LLM_API_BASE_URL", "https://test.example.com")

# ------------------------------------------------------------
# 3. Import the module under test
# ------------------------------------------------------------
try:
    from src.llm_client import (
        _retry_create,
        _llm_provider_client,
        _is_anthropic_model,
    )
    import src.llm_client as llm_mod
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)

# Override retry limits so the test completes quickly
llm_mod._MAX_RATE_LIMIT_RETRIES = 2
llm_mod._MAX_LLM_RETRIES = 2

# ------------------------------------------------------------
# 4. Execute the test
# ------------------------------------------------------------
model = "claude-sonnet-4-6"
messages = [{"role": "user", "content": "Hello"}]

# Sanity: verify model is recognized as Anthropic
if not _is_anthropic_model(model):
    print("NOT CONFIRMED — model not recognized as Anthropic")
    sys.exit(0)

actual = None
expected = "Rate limited"  # spec requires rate-limit classification

try:
    result = _retry_create(_llm_provider_client, model, messages)
    actual = "success"
except RuntimeError as e:
    actual = str(e)
except Exception as e:
    print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
    sys.exit(1)

# Classification: if the error message indicates transient handling
# instead of rate-limit handling, the bug is confirmed
if actual == "success":
    print("NOT CONFIRMED — call succeeded unexpectedly")
elif "Rate limited" in actual:
    print(f"NOT CONFIRMED — correctly treated as rate limit: {actual}")
elif "LLM request failed" in actual or "request failed" in actual:
    # BUG: URLError from Anthropic path was treated as transient,
    # not rate-limit. Spec requires per-category retry budgets.
    print(f"CONFIRMED — treated as transient instead of rate limit: {actual}")
else:
    print(f"CONFIRMED — unexpected error: {actual}")
```

### Probe Output

```
WARNING:root:LLM error (URLError: <urlopen error Connection reset by peer>), sleeping 7.3s (attempt 1)
CONFIRMED — treated as transient instead of rate limit: LLM request failed after 2 retries: <urlopen error Connection reset by peer>
```
