# [SPEC]
# Unit: src/prompts-py/_generate_block_post_condition.py
#
# _generate_block_post_condition(block, pre_condition, knowledge, language, trace_dir=None, trace_meta=None)
#
# Pre-condition:
#   - block is a non-empty string containing code statements, possibly with "Line N:" prefixes
#   - pre_condition is a non-empty string describing the logical state assumed to hold before block begins execution
#   - knowledge is an optional string providing additional contextual information that may be included in the prompt; may be empty, None, or otherwise falsy
#   - language is a non-empty string identifying the source programming language of the code in block
#   - trace_dir, when not None, is a directory path used for persisting trace records
#   - trace_meta, when not None, is a dict of metadata for trace annotation
#
# Post-condition:
#   - Returns a string describing the strongest post-condition that must hold after executing block from the given pre-condition, covering all execution paths through the block including normal flow-through, early returns, and exceptional exits
#   - Returns None when the post-condition could not be determined from the given inputs
#   - The returned post-condition is expressed in natural language suitable for subsequent logical implication checks against specification post-conditions
# [SPEC]

# [INFO]
#
# _llm_json_call(client, model, messages, parse_fn, default, trace_dir=None, trace_meta=None) -> str | None
#   Sends messages to the LLM JSON API using the given client and model, parses the LLM response with parse_fn, and returns the extracted post-condition string or None on failure.
# [INFO]

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
