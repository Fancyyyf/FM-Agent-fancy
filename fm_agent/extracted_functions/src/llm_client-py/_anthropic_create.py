# [SPEC]
# Unit: src/llm_client.py
#
# _anthropic_create(model, messages) -> (str, dict)
#
# Pre-condition:
#   - model is a non-empty string naming an Anthropic-compatible model
#   - messages is a list of message dictionaries, each with "role" and "content" keys
#   - Global variables LLM_API_BASE_URL and LLM_API_KEY are defined and non-empty
#   - _ANTHROPIC_MAX_TOKENS is a defined positive integer
#
# Post-condition:
#   - Sends the messages to the Anthropic-compatible API endpoint at LLM_API_BASE_URL/messages using the Anthropic native messages format and returns the text response and usage metadata
#   - On success, returns a tuple (text, usage_dict) where text is the concatenated string of all text-type content blocks from the response, and usage_dict is a dictionary of token-usage counts from the response (or an empty dict when no usage data is present in the response)
#   - System messages extracted from the input messages are sent with ephemeral cache-control markers for prompt caching
#   - When no system message is extracted from the input messages, an empty system block list is sent
#   - When no non-system messages remain after system extraction, a fallback single user message with empty content is sent
#   - The HTTP request uses a 600-second timeout
#   - If the response body is not valid JSON, raises RuntimeError with the HTTP status code, body size, and a truncated preview of the raw response body
# [SPEC]

# [INFO]
# _messages_to_anthropic(messages) -> (str, list)
#   Pre-condition: messages is a list of dicts with "role" and "content" keys
#   Post-condition: returns (system_text, anthropic_messages) where system_text is the concatenated text content of all system-role messages in messages (or an empty string if none), and anthropic_messages is the list of non-system messages converted to Anthropic API format
# [SPLIT]
# _should_inject_user_id(base_url) -> bool
#   Pre-condition: base_url is a non-empty string
#   Post-condition: returns True if the given base URL matches a configured provider that requires user-id metadata injection into request bodies; returns False otherwise
# [SPLIT]
# _metadata_body() -> dict
#   Pre-condition: none (takes no arguments)
#   Post-condition: returns a dictionary of metadata key-value pairs to inject into the API request body for provider-specific requirements
# [INFO]

def _anthropic_create(model, messages):
    """Send messages via an Anthropic-native /v1/messages endpoint with prompt caching.

    Returns (text, usage_dict). usage_dict matches anthropic-style:
      {input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens, ...}
    """
    system_text, an_msgs = _messages_to_anthropic(messages)

    sys_blocks = []
    if system_text:
        # cache_control marks the prefix as cacheable; ephemeral = 5-minute TTL.
        sys_blocks.append({
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        })

    body = {
        "model": model,
        "max_tokens": _ANTHROPIC_MAX_TOKENS,
        "system": sys_blocks,
        "messages": an_msgs or [{"role": "user", "content": ""}],
    }

    url = LLM_API_BASE_URL.rstrip("/") + "/messages"
    if _should_inject_user_id(LLM_API_BASE_URL):
        body.update(_metadata_body())
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        status = getattr(r, "status", None) or r.getcode()
        body_bytes = r.read()
    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        # The relay returned a non-JSON / empty body (e.g. an empty 200 or an
        # HTML error page truncated by the proxy under load). Surface the raw
        # body + status — otherwise only "Expecting value: line 1 column 1" leaks
        # and the actual relay response is lost.
        snippet = body_bytes[:800].decode("utf-8", "replace")
        raise RuntimeError(
            f"non-JSON response from relay (HTTP {status}, {len(body_bytes)} bytes): {snippet!r}"
        ) from exc
    # Anthropic content is a list of blocks; concatenate text blocks.
    text = "".join(c.get("text", "") for c in data.get("content", []) if c.get("type") == "text")
    usage = data.get("usage", {}) or {}
    return text, usage
