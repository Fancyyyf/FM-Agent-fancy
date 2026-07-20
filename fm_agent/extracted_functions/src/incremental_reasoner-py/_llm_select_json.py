# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_llm_select_json.py
#
# _llm_select_json(work_dir, prompt_content, stage, validator, schema_description, trace_meta=None) -> dict | list | None
#
# Pre-condition:
#   - work_dir is a path to a writable directory containing a trace/ subdirectory
#   - prompt_content is a non-empty string forming a complete LLM prompt
#   - stage is a non-empty string identifying the pipeline stage for logging and tracing
#   - validator is a callable that accepts a single decoded JSON value (dict or list)
#     and returns a truthy value when validation passes, or raises/returns falsy on failure
#   - schema_description is a non-empty string describing the expected JSON schema
#   - trace_meta is None or a dict of trace metadata key-value pairs
#
# Post-condition:
#   - Sends prompt_content as a single user-turn message to the configured LLM provider
#     using the configured model
#   - Accepts exactly one JSON object or array from the LLM response, including responses
#     wrapped in markdown fences or prose text
#   - Validates the parsed JSON value against the validator callable
#   - Retries the LLM call on protocol-level failures (connection, parsing, or validation
#     failures)
#   - Returns the parsed-and-validated JSON value (dict or list) when validation succeeds
#   - Returns None when no valid JSON response is obtained after all retries are exhausted
#   - Records every LLM exchange (request and response) to the trace directory under
#     work_dir/trace/
#   - Logs an error-level message identifying the stage when the result is None
# [SPEC]

# [INFO]
# _llm_json_call(client, model, messages, validator, schema_description, trace_dir, trace_meta) -> dict | list | None
#   Pre-condition: client is a configured LLM provider client capable of sending chat messages; model is a model identifier string; messages is a non-empty list of message dicts each with "role" and "content" keys; validator is a callable accepting a single decoded JSON value and returning truthy on success; schema_description is a string describing the expected JSON schema; trace_dir is a writable directory path; trace_meta is a dict of trace metadata
#   Post-condition: Sends messages to the LLM, receives exactly one JSON object or array (optionally fenced or prose-wrapped), validates the parsed value against validator, retries on protocol-level failures; returns the validated JSON value on success, None when all retries are exhausted
# [INFO]

def _llm_select_json(work_dir, prompt_content, stage, validator, schema_description,
                     trace_meta=None):
    """Run a direct LLM call and return validated structured JSON.

    This is for self-contained prompts whose context is already inlined. The
    shared JSON caller records the raw exchange, accepts exactly one JSON
    object or array (including a fenced or prose-wrapped one), validates the
    required fields, and retries on protocol failures.
    """
    messages = [{"role": "user", "content": prompt_content}]
    meta = {"stage": stage, "summary": f"LLM {stage}", **(trace_meta or {})}
    result = _llm_json_call(
        _llm_provider_client,
        LLM_MODEL,
        messages,
        validator,
        schema_description,
        trace_dir=os.path.join(work_dir, "trace"),
        trace_meta=meta,
    )
    if result is None:
        logging.error("%s: LLM produced no valid JSON response after retries.", stage)
    return result
