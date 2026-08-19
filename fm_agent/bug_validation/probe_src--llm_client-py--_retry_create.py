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
