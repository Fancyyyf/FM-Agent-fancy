def _llm_json_call(client, model, messages, validator, schema_description,
                   max_retries=MAX_SPC_ITER, trace_dir=None, trace_meta=None):
    """Call an LLM until it returns structured JSON accepted by ``validator``.

    ``validator`` receives the parsed JSON value and must either return the
    desired Python value or raise ``ValueError`` with a schema error. Keeping
    JSON parsing and retry handling in one place makes every direct structured
    LLM call follow the same protocol.
    """
    trace_meta = trace_meta or {}
    for attempt in range(1, max_retries + 1):
        event_id = new_event_id("llm")
        started = utc_now_iso()
        response = None
        usage = {}
        try:
            response, usage = _retry_create(client, model, messages)
        except Exception as exc:
            event = {
                "event_id": event_id,
                "type": "llm_call",
                "stage": "verification",
                "status": "error",
                "start_time": started,
                "end_time": utc_now_iso(),
                "summary": f"LLM call failed: {exc}",
                "metadata": {
                    **trace_meta,
                    "model": model,
                    "attempt": attempt,
                    "error": str(exc),
                },
            }
            record_llm_exchange(trace_dir, event_id, event, messages)
            raise

        parsed_json = None
        result = None
        parse_error = None
        try:
            parsed_json = _parse_json_response(response)
            result = validator(parsed_json)
            status = "success"
        except ValueError as exc:
            parse_error = str(exc)
            status = "format_error"

        event = {
            "event_id": event_id,
            "type": "llm_call",
            "stage": "verification",
            "status": status,
            "start_time": started,
            "end_time": utc_now_iso(),
            "summary": trace_meta.get("summary", "LLM JSON call"),
            "metadata": {
                **trace_meta,
                "model": model,
                "attempt": attempt,
                "usage": usage,
                "parsed_json": parsed_json,
                "parse_error": parse_error,
            },
        }
        record_llm_exchange(trace_dir, event_id, event, messages, response)
        if status == "success":
            return result

        messages = messages + [
            {"role": "assistant", "content": response or ""},
            {"role": "user", "content": (
                f"Your previous response was invalid: {parse_error}. "
                f"Return only valid JSON matching this schema: {schema_description}. "
                "Do not include Markdown, tags, or prose."
            )},
        ]
    return None
