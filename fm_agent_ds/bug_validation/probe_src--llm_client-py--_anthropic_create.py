#!/usr/bin/env python3
"""Probe for bug src--llm_client-py--_anthropic_create.

Bug: _anthropic_create returns an empty string when the API response contains
no content blocks of type "text" (e.g., only tool_use blocks). The spec
requires text to be a non-empty string.

This probe mocks urllib.request.urlopen to simulate such a response.
"""

import os
import sys

# The probe lives under fm_agent/bug_validation/; add the repo root to
# sys.path so that `import src.llm_client` and `from config import *` resolve.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

import json
import urllib.request

# ── Mock urllib BEFORE importing src.llm_client ──────────────────────────
# The module accesses urllib.request.urlopen at call time, so replacing it
# before import is the cleanest way to intercept the HTTP call.

MOCK_RESPONSE_BODY = json.dumps({
    "id": "msg_001",
    "type": "message",
    "role": "assistant",
    "content": [
        {"type": "tool_use", "id": "t_001", "name": "get_current_time", "input": {}}
    ],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "tool_use",
    "usage": {"input_tokens": 50, "output_tokens": 20},
}).encode("utf-8")


class _MockHTTPResponse:
    """Fake urllib response with no text-type content blocks in the body."""

    def __init__(self):
        self.status = 200

    def getcode(self):
        return 200

    def read(self):
        return MOCK_RESPONSE_BODY

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


_original_urlopen = urllib.request.urlopen


def _mock_urlopen(req, timeout=None, **__):
    return _MockHTTPResponse()


urllib.request.urlopen = _mock_urlopen

# ── Import the package via its public entry point ────────────────────────
import src.llm_client as llm_client


def main():
    try:
        text, usage = llm_client._anthropic_create(
            model="claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": "What time is it?"}],
        )

        # Bug: when the response content has no text-type blocks, text is
        # empty. The spec says text MUST be a non-empty string.
        bug_confirmed = text == ""

        if bug_confirmed:
            print(
                f"CONFIRMED — actual: {text!r} (empty string) "
                f"| expected per spec: non-empty string"
            )
        else:
            print(
                f"NOT CONFIRMED — actual: {text!r} (non-empty, spec satisfied)"
            )

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Restore original urlopen
        urllib.request.urlopen = _original_urlopen


if __name__ == "__main__":
    main()
