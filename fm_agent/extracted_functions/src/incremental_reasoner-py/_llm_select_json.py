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
