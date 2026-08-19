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
