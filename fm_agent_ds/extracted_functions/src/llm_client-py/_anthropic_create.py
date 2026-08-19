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
