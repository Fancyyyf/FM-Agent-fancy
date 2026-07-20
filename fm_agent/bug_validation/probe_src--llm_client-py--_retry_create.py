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
