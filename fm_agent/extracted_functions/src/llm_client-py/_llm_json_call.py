# [SPEC]
# Unit: src/llm_client-py/_llm_json_call.py
#
# _llm_json_call(client, model, messages, validator, schema_description, max_retries=MAX_SPC_ITER, trace_dir=None, trace_meta=None) -> Any | None
#
# Pre-condition:
#   - client can send conversation messages for the given model and return a text response
#   - model is a non-empty string identifying the LLM to use
#   - messages is a list of conversation message dicts, each with at least "role" and "content" keys
#   - validator is a callable that accepts a parsed JSON value (dict, list, str, int, float, bool, or None) and returns a result or raises ValueError with an error message
#   - schema_description is a string describing the expected JSON structure
#   - max_retries is a positive integer
#   - trace_dir is a writable directory path or None
#   - trace_meta is a dict optionally containing a "summary" key
#
# Post-condition:
#   - Up to max_retries attempts are made to obtain a JSON response from the LLM that validator accepts
#   - On each attempt, the current conversation messages are sent to the LLM and a text response is received; if sending fails, the failure is durably recorded and the exception is re-raised without further retries
#   - Each received text response is parsed as JSON; if parsing succeeds and validator returns a value without raising ValueError, that value becomes the function result; the successful outcome is durably recorded
#   - If parsing fails or validator raises ValueError, the conversation is extended with the rejected response text and a corrective user message that includes the error description and schema_description; the failed outcome is durably recorded, and the next attempt proceeds with the extended conversation
#   - After max_retries attempts without validator acceptance, returns None
#   - Every LLM attempt produces a durable outcome record containing: attempt number, start and end timestamps, status (one of "success", "format_error", or "error"), model identifier, usage metadata, the parsed JSON value (when parsing succeeds), and the error message (on format error or LLM failure)
# [SPEC]

# [INFO]
# new_event_id(prefix) -> str
#   Pre-condition: prefix is a non-empty string
#   Post-condition: returns a unique identifier string not equal to any previously returned identifier
# [SPLIT]
# utc_now_iso() -> str
#   Pre-condition: none
#   Post-condition: returns the current UTC date and time as an ISO 8601 formatted string
# [SPLIT]
# _retry_create(client, model, messages) -> (str, dict)
#   Pre-condition: client can send messages for model and return a text response; model is a non-empty string; messages is a list of message dicts
#   Post-condition: returns a tuple of (response_text, usage_metadata_dict); raises an exception if the LLM cannot be reached
# [SPLIT]
# _parse_json_response(response) -> Any
#   Pre-condition: response is a string
#   Post-condition: returns the JSON value parsed from response (dict, list, str, int, float, bool, or None); raises ValueError if response is not syntactically valid JSON
# [SPLIT]
# record_llm_exchange(trace_dir, event_id, event, messages, response=None) -> None
#   Pre-condition: event_id is a string; event is a dict; messages is a list of message dicts
#   Post-condition: persists the event and associated data under trace_dir; has no effect when trace_dir is None
# [INFO]

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
