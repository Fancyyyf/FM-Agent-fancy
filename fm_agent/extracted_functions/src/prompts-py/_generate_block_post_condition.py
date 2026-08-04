def _generate_block_post_condition(block, pre_condition, knowledge, language,
                                   trace_dir=None, trace_meta=None):
    info_str = f"\nAdditional context:\n{knowledge}" if knowledge else ""
    messages = [
        {"role": "system", "content": (
            f"You are an expert in formal verification of {language} programs. "
            f"Given a {language} code block and its pre-condition, generate the post-condition "
            "that describes the program state after the code block finishes execution. "
            "Cover all execution paths including early returns, exceptions, and normal flow-through. "
            f"Apply {language}-specific semantics (ownership, lifetimes, error handling, etc.) as appropriate. "
            "Be precise and unambiguous. Express the post-condition in natural language and formal logic."
        )},
        {"role": "user", "content": (
            f"Programming language: {language}\n\n"
            f"Pre-condition:\n{pre_condition}\n\n"
            f"Code block:\n```{language.lower()}\n{block}\n```\n"
            f"{info_str}\n"
            "Generate the post-condition. Return only a valid JSON object with this "
            "required field: {\"post_condition\": \"...\"}. Do not include Markdown, "
            "tags, or prose outside the JSON object."
        )}
    ]
    meta = {
        "purpose": "generate_block_post_condition",
        "summary": "Generated post-condition for code block",
        **(trace_meta or {}),
    }
    return _llm_json_call(
        _llm_provider_client,
        REASONER_POST_CONDITION_MODEL,
        messages,
        _parse_post_condition_json,
        '{"post_condition": "non-empty string"}',
        trace_dir=trace_dir,
        trace_meta=meta,
    )
