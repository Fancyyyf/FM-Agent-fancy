"""Probe script for resolve_model_backend bug: when FM_AGENT_MODEL_BACKEND
is not set, the function returns "opencode" via _normalize_backend's
fallback instead of running auto-detection against environment markers.

Spec requirement: when FM_AGENT_MODEL_BACKEND is absent, the function
should inspect environment markers (CLAUDE_PLUGIN_ROOT, CODEX_HOME, etc.)
and return the corresponding backend. Setting a Claude marker like
CLAUDE_PLUGIN_ROOT should yield "claude-cli".

Actual (buggy) behavior: _normalize_backend(None) returns "opencode" because
(None or "") -> "", and not "" is True -> returns "opencode". Then the
condition backend != "auto" is True, so it returns "opencode" immediately
without checking any environment markers.
"""

import os
import sys

# Add repo root to path so 'src' package is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the module. Note: load_dotenv() runs at import time; since no .env
# file exists in this snapshot, no env vars are modified.
from src.cli_backend import resolve_model_backend

# Ensure FM_AGENT_MODEL_BACKEND is NOT set (load_dotenv may have added it
# if a .env file existed, but here it does not).
os.environ.pop("FM_AGENT_MODEL_BACKEND", None)

# Set a Claude-specific marker so auto-detection would find it if reached.
os.environ["CLAUDE_PLUGIN_ROOT"] = "/tmp/test-claude-plugin-root"

try:
    actual = resolve_model_backend()

    # Per spec: when FM_AGENT_MODEL_BACKEND is absent, auto-detection should
    # see CLAUDE_PLUGIN_ROOT and return "claude-cli".
    expected = "claude-cli"

    # Bug confirmed when actual does NOT match expected.
    # The buggy code returns "opencode" (via _normalize_backend fallback)
    # instead of "claude-cli" (via auto-detection).
    passed = actual != expected
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
