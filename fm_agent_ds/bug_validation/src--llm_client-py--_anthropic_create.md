# Bug Report: _anthropic_create

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/llm_client.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Sends a prompt-cached chat completion request to the Anthropic /v1/messages API and returns a 2-tuple (text, usage). text is the non-empty string formed by concatenating, in order, all text-type content blocks from the API response. usage is a dict mapping token-usage metric names to their integer counts from the API response (empty dict when no usage data is present). The system-role messages from the input are transmitted with ephemeral cache-control annotations. When the input messages consist solely of system-role messages, a minimal user message is included to satisfy the API requirement. Requests are made with a fixed maximum token budget. On receipt of a response body that is not valid JSON, raises RuntimeError whose message includes the HTTP status code and a prefix of the raw response bytes. HTTP transport failures propagate to the caller as HTTPError or URLError.

---

### Actual Behavior

After execution of _anthropic_create, the program state is one of the following: (1) The function returns a 2-tuple (text, usage_dict). text is a non-empty string obtained by concatenating the "text" fields of all response content blocks whose "type" is "text". usage_dict is a dictionary containing the token usage information from the API (keys such as input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens) or an empty dictionary if the response lacks a "usage" key. (2) The function raises a RuntimeError if the API response body cannot be decoded as JSON (JSONDecodeError); the exception message includes the HTTP status code, the length of the response body, and a snippet of the raw body. (3) The function propagates any exception occurring during the HTTP request (e.g., HTTPError, URLError, socket.timeout) without modification. Formal logic: R  {Return(text, usage) | isinstance(text, str)  text = concat({c["text"] | c  data["content"]  c["type"] == "text"})  usage = data.get("usage", {}) }  {Raise(RuntimeError) | message contains "non-JSON response from relay"  cause is JSONDecodeError}  {Raise(E) | E is any exception from urllib.request.urlopen or json.loads' chain }, where data is the JSON-parsed response dict when parsing succeeds.

---

## Code Evidence

Line 49: text = "".join(c.get("text", "") for c in data.get("content", []) if c.get("type") == "text")

---

## Trigger Condition

The code does not guarantee that the returned text string is non-empty. When the API response contains no content blocks of type "text", text becomes an empty string, violating the specification's requirement that text is a non-empty string.

---

## How to trigger the bug

When the Anthropic API responds with only non-text content blocks (e.g., tool_use blocks), the concatenation loop produces an empty string, violating the spec's "non-empty" requirement.

### Inputs

| Parameter | Value |
|-----------|-------|
| `model` | `"claude-sonnet-4-20250514"` |
| `messages` | `[{"role": "user", "content": "What time is it?"}]` |
| Mocked API response content | `[{"type": "tool_use", "id": "t_001", "name": "get_current_time", "input": {}}]` |

### Expected (spec-correct) Output

Non-empty string (concatenated text from all text-type content blocks). Since the spec requires a non-empty string, the function should raise an error or ensure the result is non-empty when no text blocks are present.

### Actual (buggy) Output

`""` (empty string) — the join comprehension yields an empty string because no content block has `type` == `"text"`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Mock the HTTP response to return only tool_use-type content blocks.
3. Run the following snippet (uses the package entry point):

```python
import json
import urllib.request

class MockResponse:
    status = 200
    def getcode(self): return 200
    def read(self):
        return json.dumps({
            "content": [{"type": "tool_use", "id": "t1", "name": "f", "input": {}}],
            "usage": {"input_tokens": 10, "output_tokens": 5}
        }).encode()
    def __enter__(self): return self
    def __exit__(self, *a): pass

_orig = urllib.request.urlopen
urllib.request.urlopen = lambda *a, **kw: MockResponse()

import src.llm_client as m
text, usage = m._anthropic_create("claude-sonnet-4-20250514",
    [{"role": "user", "content": "hi"}])
# actual (buggy) output: ""
# expected (correct) output: non-empty string

urllib.request.urlopen = _orig
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: '' (empty string) | expected per spec: non-empty string
```
