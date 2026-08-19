# Bug Report: _retry_create

**Source file:** `src/llm_client-py/_retry_create.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Issues one logical completion request for model with messages and returns a tuple (response_text, usage): response_text is the model's raw completion string, and usage is a dict of provider-reported usage that is empty ({}) when the provider reports no usage or when the request is served by a local CLI agent backend. Backend selection is governed by configuration: when a local CLI agent backend is enabled, the request is served by that backend and its (text, {}) result is returned unchanged. Otherwise the request goes over HTTP, routed to the native Anthropic messages endpoint for Anthropic-family model names and to the OpenAI-compatible completions endpoint for all other model names; when the configured base URL matches a provider-injection target, a metadata body carrying a stable user id is attached to the request without altering the conversation content. Error contract: invalid-request failures (BadRequestError, or HTTP 400 from the relay) raise immediately and are never retried. Rate-limit failures (HTTP 429 or RateLimitError) are retried with exponentially growing, capped delays plus jitter up to 20 attempts, after which RuntimeError is raised with the last failure chained. All other transient failures (other HTTP errors, any other exception) are retried with exponentially growing, capped delays plus jitter up to 5 attempts, after which RuntimeError is raised with the last failure chained. HTTP-error details surfaced in warnings and RuntimeErrors include the relay's raw error body when one is available. Messages and client state are never mutated by retries. Success returns only after a transport-level success; the function never returns None.

---

### Actual Behavior

The function _retry_create terminates in exactly one of the following outcomes:

**Normal return (tuple (text: str, usage: dict)):**

1. *CLI-backend path:* If is_cli_backend_enabled() returned True, the function returns the result of run_agent_for_messages(model, messages), i.e., a tuple (text, {}) where text is the local agent's stripped stdout. The HTTP client argument is never dereferenced.

2. *Anthropic HTTP path:* If is_cli_backend_enabled() returned False and _is_anthropic_model(model) returned True, the function returns the result of _anthropic_create(model, messages), i.e., (response_text, usage_dict) from the native Anthropic /v1/messages endpoint. The OpenAI-compat client is never invoked.

3. *OpenAI-compatible HTTP path:* If is_cli_backend_enabled() returned False and _is_anthropic_model(model) returned False, the function returns (text, usage) where text == response.choices[0].message.content and usage == response.usage.model_dump() if response.usage is truthy, else usage == {}. The call is client.chat.completions.create(model=model, messages=messages, **extra) where extra == {"extra_body": _metadata_body()} if _should_inject_user_id(LLM_API_BASE_URL) was True, else extra == {}.

In all normal-return cases, text is a str and usage is a dict.

**Exception propagation (function does not return normally):**

4. *BadRequestError:* Any BadRequestError raised inside the try block is re-raised immediately without retry.

5. *HTTP 400:* An urllib.error.HTTPError with exc.code == 400 is re-raised immediately without retry.

6. *Rate-limit exhaustion (HTTP 429 or RateLimitError):* After _MAX_RATE_LIMIT_RETRIES consecutive 429/RateLimitError failures (with exponential back-off sleeps of min(2^(n-1)*5, 300) + uniform(1,10) seconds between attempts), a RuntimeError is raised whose message contains 'Rate limited after {_MAX_RATE_LIMIT_RETRIES} retries' and whose __cause__ is the last triggering exception.

7. *Transient-error exhaustion (HTTP 5xx / other HTTPError / generic Exception):* After _MAX_LLM_RETRIES consecutive transient failures (with exponential back-off sleeps of min(2^(n-1)*5, 60) + uniform(1,3) seconds between attempts), a RuntimeError is raised whose message contains 'LLM request failed after {_MAX_LLM_RETRIES} retries' and whose __cause__ is the last triggering exception.

8. *CLI subprocess failure:* If the CLI-backend path is taken and the subprocess exits non-zero or times out, the RuntimeError from run_agent_for_messages propagates unmodified.

9. *Anthropic relay decode failure:* If the Anthropic path is taken and the relay response is not decodable JSON, the RuntimeError from _anthropic_create propagates unmodified.

**Invariants across all paths:**
- model and messages are never mutated.
- client is dereferenced only on the OpenAI-compatible HTTP path (path 3 and its retries); it is never accessed on the CLI or Anthropic paths.
- The retry counters rate_limit_attempts and transient_attempts are local and monotonically non-decreasing within a single invocation; they are never reset.
- No partial response is returned: the function either returns a complete (text, usage) tuple or raises.
- Formally:  execution e of _retry_create(client, model, messages): ( tstr, udict: e returns (t, u))  (e raises BadRequestError)  (e raises urllib.error.HTTPError  exc.code==400)  (e raises RuntimeError).

---

## Code Evidence

Line 19:                 return _anthropic_create(model, messages)

---

## Trigger Condition

The specification states: 'when the configured base URL matches a provider-injection target, a metadata body carrying a stable user id is attached to the request without altering the conversation content.' This applies to every HTTP request, whether routed to the Anthropic endpoint or the OpenAI-compatible endpoint. The code computes the metadata in the extra dict (Lines 13-15) but only spreads it into the OpenAI-compatible call on Line 20 via **extra. On the Anthropic path, Line 19 calls _anthropic_create(model, messages) without passing the extra/metadata at all, and _anthropic_create's signature accepts only (model, messages) with no metadata parameter. Therefore, when an Anthropic-family model is used and the base URL matches the injection target, the user_id metadata is silently omitted from the request, violating the specification.

---

## How to trigger the bug

The probe configured the package so that the HTTP Anthropic path is taken with provider injection enabled: CLI backend disabled (`FM_AGENT_MODEL_BACKEND=opencode`), `LLM_API_BASE_URL` pointed at a base URL that matches the configured injection target (`INJECT_HOST`), and a stable user id configured (`INJECT_ID`). It then called `src.llm_client._retry_create` with an Anthropic-family model name and intercepted the outgoing HTTP request at the transport layer (`urllib.request.urlopen`), inspecting the exact JSON body posted to the native `/v1/messages` endpoint.

**Result:** the reported omission does not exist in the composed code. Although `_retry_create` indeed does not pass its `extra` dict to `_anthropic_create`, `_anthropic_create` performs the injection itself: it evaluates `_should_inject_user_id(LLM_API_BASE_URL)` and merges `_metadata_body()` into the request body (`src/llm_client.py`, inside `_anthropic_create`). The captured Anthropic request body carried `metadata.user_id` equal to the configured stable user id, and the conversation content was unaltered. The verification gap appears to stem from analyzing the extracted `_retry_create` function in isolation, without the body of its callee `_anthropic_create`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `client` | `src.llm_client._llm_provider_client` (module-level OpenAI client) |
| `model` (attempt 2) | `claude-sonnet-4-6` |
| `model` (attempt 3) | `anthropic/claude-opus-4-6` |
| `messages` | `[{"role": "system", "content": "You are the probe system."}, {"role": "user", "content": "ping"}]` |
| `LLM_API_BASE_URL` (attempt 2) | `https://relay.example-inject.com/v1` |
| `LLM_API_BASE_URL` (attempt 3) | `https://relay2.example.com/v1` |
| `INJECT_HOST` (attempt 2) | `relay.example-inject.com` (hostname-match branch) |
| `INJECT_HOST` (attempt 3) | `https://relay2.example.com/v1` (full-URL startswith branch) |
| `INJECT_ID` (attempt 2 / 3) | `stable-probe-user-42` / `second-stable-user-777` |
| `FM_AGENT_MODEL_BACKEND` | `opencode` (CLI backend disabled) |

### Expected (spec-correct) Output

The POST body sent to `<LLM_API_BASE_URL>/messages` must contain `"metadata": {"user_id": "<INJECT_ID>"}` while leaving the conversation content unaltered, e.g. `body["metadata"]["user_id"] == "stable-probe-user-42"`.

### Actual (buggy) Output

No buggy output was observed — the actual behavior matched the specification. The captured Anthropic request body contained `metadata.user_id='stable-probe-user-42'` (attempt 2) and `metadata.user_id='second-stable-user-777'` (attempt 3), with the conversation content intact in both attempts. The claimed silent omission of `user_id` metadata on the Anthropic path did not occur, so the bug could not be reproduced within the attempt budget.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import os, sys, io, json, urllib.request
os.environ["LLM_API_KEY"] = "probe-dummy-key"
os.environ["LLM_API_BASE_URL"] = "https://relay.example-inject.com/v1"
os.environ["INJECT_HOST"] = "relay.example-inject.com"
os.environ["INJECT_ID"] = "stable-probe-user-42"
os.environ["FM_AGENT_MODEL_BACKEND"] = "opencode"

captured = {}
class FakeResp:
    def __init__(self, payload): self._b = io.BytesIO(payload); self.status = 200
    def read(self, n=-1): return self._b.read(n)
    def getcode(self): return self.status
    def __enter__(self): return self
    def __exit__(self, *a): return False
def fake_urlopen(req, timeout=None):
    captured["body"] = json.loads(req.data.decode("utf-8"))
    return FakeResp(json.dumps({"content": [{"type": "text", "text": "ok"}],
                                "usage": {"input_tokens": 1, "output_tokens": 1}}).encode())
urllib.request.urlopen = fake_urlopen

import src.llm_client as llm_client
llm_client._retry_create(llm_client._llm_provider_client, "claude-sonnet-4-6",
                         [{"role": "user", "content": "ping"}])
print(captured["body"].get("metadata"))
// actual output: {'user_id': 'stable-probe-user-42'}  (metadata IS present)
// output claimed by the bug report: metadata key omitted (NOT observed)
```

---

## Probe Script

```py
"""Probe for bug src--llm_client-py--_retry_create.

Claim under test (from the verification gap):
  When an Anthropic-family model is used and LLM_API_BASE_URL matches a
  provider-injection target, the request served by the Anthropic
  /v1/messages endpoint silently omits the metadata.user_id body that the
  specification requires on every HTTP request ("when the configured base
  URL matches a provider-injection target, a metadata body carrying a
  stable user id is attached to the request without altering the
  conversation content").

Strategy (unit-level, per the FM-Agent self-validation guard — no FM-Agent
workflow, CLI, or subprocess is started):
  * Configure the package through its documented env overrides so that
      - the CLI backend is disabled          (FM_AGENT_MODEL_BACKEND=opencode)
      - the base URL matches the injection target (INJECT_HOST)
      - a stable user id is configured        (INJECT_ID)
  * Load the package through its entry point (`import src.llm_client`).
  * Intercept the outgoing HTTP request at the transport layer:
      - Anthropic path: patched urllib.request.urlopen captures the POST body.
      - OpenAI-compatible path (control): OpenAI client with an
        httpx.MockTransport captures the POST body.
  * Oracle: the Anthropic request body must carry
    metadata.user_id == INJECT_ID and must not alter the conversation
    content. Bug reproduced (CONFIRMED) iff the metadata is absent/wrong.

Self-contained: no network access, no files written.
"""

import io
import json
import os
import sys

BASE_URL = "https://relay2.example.com/v1"
INJECT_HOST = "https://relay2.example.com/v1"  # full-URL target (startswith branch)
INJECT_ID = "second-stable-user-777"

# env > .env > fm-agent.toml precedence (see config.py)
os.environ["LLM_API_KEY"] = "probe-dummy-key"
os.environ["LLM_API_BASE_URL"] = BASE_URL
os.environ["INJECT_HOST"] = INJECT_HOST
os.environ["INJECT_ID"] = INJECT_ID
os.environ["FM_AGENT_MODEL_BACKEND"] = "opencode"  # keep the HTTP path active

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    import urllib.request

    import src.llm_client as llm_client  # loads via the src package entry point
    import httpx
    from openai import OpenAI

    # ---- capture the Anthropic-native /v1/messages request ----------------
    anthropic_capture = {}

    class _FakeHTTPResponse:
        """Minimal stand-in for the urllib response used by _anthropic_create."""

        def __init__(self, payload, status=200):
            self._buf = io.BytesIO(payload)
            self.status = status

        def read(self, n=-1):
            return self._buf.read(n)

        def getcode(self):
            return self.status

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _fake_urlopen(req, timeout=None):
        anthropic_capture["url"] = req.full_url
        anthropic_capture["body"] = json.loads(req.data.decode("utf-8"))
        payload = json.dumps({
            "id": "msg_probe",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "probe-reply"}],
            "usage": {"input_tokens": 11, "output_tokens": 7},
        }).encode("utf-8")
        return _FakeHTTPResponse(payload)

    urllib.request.urlopen = _fake_urlopen

    # ---- capture the OpenAI-compatible /chat/completions request (control) -
    openai_capture = {}

    def _mock_handler(request):
        openai_capture["url"] = str(request.url)
        openai_capture["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-probe",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "probe-model",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 1,
                    "total_tokens": 6,
                },
            },
        )

    mock_openai_client = OpenAI(
        api_key="probe-dummy-key",
        base_url=BASE_URL,
        http_client=httpx.Client(transport=httpx.MockTransport(_mock_handler)),
    )

    messages = [
        {"role": "system", "content": "You are the probe system."},
        {"role": "user", "content": "ping"},
    ]

    if llm_client.is_cli_backend_enabled():
        raise AssertionError("CLI backend unexpectedly enabled; HTTP path not taken")

    # 1) Anthropic-family model -> native /v1/messages path (the reported bug)
    an_text, an_usage = llm_client._retry_create(
        llm_client._llm_provider_client, "anthropic/claude-opus-4-6", messages)

    # 2) non-Anthropic model -> OpenAI-compatible path (control)
    oa_text, oa_usage = llm_client._retry_create(
        mock_openai_client, "probe-model", messages)

    an_body = anthropic_capture.get("body", {})
    an_meta = (an_body.get("metadata") or {}).get("user_id")
    oa_body = openai_capture.get("body", {})
    oa_meta = (oa_body.get("metadata") or {}).get("user_id")

    # spec: "without altering the conversation content"
    system_blocks = an_body.get("system") or []
    content_intact = (
        an_body.get("messages") == [{"role": "user", "content": "ping"}]
        and len(system_blocks) == 1
        and system_blocks[0].get("text") == "You are the probe system."
    )

    # Bug reproduction oracle: metadata must carry the stable user id.
    passed = an_meta != INJECT_ID  # True -> the reported omission exists
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

if passed:
    print(
        "CONFIRMED — Anthropic /v1/messages body omitted metadata.user_id: "
        f"metadata={an_body.get('metadata')!r} | expected metadata.user_id={INJECT_ID!r}"
    )
else:
    print(
        "NOT CONFIRMED — actual matched expected: the Anthropic /v1/messages "
        f"request carried metadata.user_id={an_meta!r} as the specification requires; "
        f"conversation content intact: {content_intact}; "
        f"OpenAI-compatible control metadata.user_id={oa_meta!r}; "
        f"anthropic url={anthropic_capture.get('url')!r}; "
        f"returns (text={an_text!r}, usage={an_usage!r}) / (text={oa_text!r}, usage={oa_usage!r})"
    )
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: the Anthropic /v1/messages request carried metadata.user_id='second-stable-user-777' as the specification requires; conversation content intact: True; OpenAI-compatible control metadata.user_id='second-stable-user-777'; anthropic url='https://relay2.example.com/v1/messages'; returns (text='probe-reply', usage={'input_tokens': 11, 'output_tokens': 7}) / (text='ok', usage={'completion_tokens': 1, 'prompt_tokens': 5, 'total_tokens': 6, 'completion_tokens_details': None, 'prompt_tokens_details': None})
```
