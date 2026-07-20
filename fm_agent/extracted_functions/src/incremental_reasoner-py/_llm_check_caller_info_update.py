# [SPEC]
# Unit: src/incremental_reasoner-py/_llm_check_caller_info_update.py
#
# _llm_check_caller_info_update(proj_dir, work_dir, idx, caller_fqn, callee_name,
#                                lang_key, comment_prefix, callee_new_spec,
#                                caller_info_block, caller_source) -> dict | None
#
# Pre-condition:
#   - proj_dir and work_dir are valid directory paths on disk
#   - idx is a non-negative integer used only for trace-event labeling
#   - caller_fqn is a non-empty FQN string identifying the caller function
#   - callee_name is a non-empty string naming the callee whose [SPEC] was updated
#   - lang_key is a valid language identifier for which comment_prefix is the
#     single-line comment marker
#   - comment_prefix is the single-line comment prefix for the source language
#   - callee_new_spec is a non-empty string containing the callee's updated
#     [SPEC] block, including its opening and closing marker lines
#   - caller_info_block is a non-empty string containing the caller's full
#     current [INFO] block, including its opening and closing marker lines
#   - caller_source is a non-empty string containing the caller's complete source
#     code, inclusive of any leading [SPEC] and [INFO] comment blocks
#
# Post-condition:
#   - Constructs an LLM prompt that asks to evaluate whether the caller's [INFO]
#     entry for callee_name is consistent with callee_new_spec; consistency means
#     no contradictory pre-condition or post-condition exists between the
#     callee's specification and the caller's recorded expectation for that
#     callee
#   - Sends the prompt to an LLM and validates the response against a JSON
#     schema requiring keys "info_updated" (bool) and "new_info" (string)
#   - When the LLM returns valid, parseable JSON, info_updated is True if and
#     only if the entry for callee_name required modification to achieve
#     consistency; when info_updated is True, new_info contains the complete
#     replacement [INFO] block (markers included, all prior callee entries
#     preserved, callee_name entry adjusted for consistency, all other entries
#     byte-for-byte unchanged); when info_updated is False, new_info is the
#     empty string
#   - Returns None when the LLM produces no response, or when the response
#     cannot be parsed as valid JSON matching the required schema
#   - Domain knowledge files from under work_dir, if any exist at the expected
#     location, are included in the prompt as additional context
#   - The function performs no file writes and does not modify caller_source
# [SPEC]

# [INFO]
# _domain_knowledge_prompt_section(work_dir) -> str
#   Pre-condition: work_dir is a valid directory path
#   Post-condition: Returns a string containing the concatenated contents of all
#     domain knowledge files found under the expected subdirectory, formatted
#     with appropriate section headers; returns an empty string when no such
#     files exist at the expected location
# [SPLIT]
# _llm_select_json(work_dir, prompt_content, stage, validator,
#                   schema_description, trace_meta) -> dict | None
#   Pre-condition: work_dir is a valid directory path; prompt_content is a
#     non-empty string; stage is a non-empty pipeline-stage identifier;
#     validator is a callable that validates the parsed JSON dict against the
#     expected schema; schema_description is a non-empty string describing the
#     expected JSON shape; trace_meta is a dict
#   Post-condition: Sends prompt_content to an LLM and collects the response
#     until completion. Validates the parsed JSON response against the expected
#     schema using the validator. Returns the parsed dict when the response is
#     valid JSON satisfying the validator. Returns None when the LLM call fails,
#     produces no response, or returns output that cannot be parsed as valid
#     JSON satisfying the validator
# [INFO]

def _llm_check_caller_info_update(proj_dir, work_dir, idx, caller_fqn, callee_name,
                                  lang_key, comment_prefix, callee_new_spec,
                                  caller_info_block, caller_source):
    """
    Ask the LLM whether a caller's [INFO] block must change to stay consistent with a callee
    whose [SPEC] block was just updated.

    The caller's [INFO] block records the expected specs of the callees it depends on. This
    asks the model to reconcile only the entry for callee_name with the callee's new spec —
    consistency, not equality: the entry must merely not conflict with the new spec, and the
    entries for other callees are left untouched. The prompt inlines the callee's new spec
    and the caller's source/[INFO], so it is issued as a direct LLM call (via
    _llm_select_json) rather than an opencode run; idx only labels the traced exchange.

    Returns the parsed result dict — keys "info_updated" (bool) and "new_info" (str) — or
    None when the LLM produced nothing usable.
    """
    knowledge_section = _domain_knowledge_prompt_section(work_dir)

    prompt_content = (
        "# Reconcile a Caller's [INFO] Block with a Changed Callee\n\n"
        f"The callee `{callee_name}`'s behavioral specification was just updated. The caller "
        f"`{caller_fqn}` (language `{lang_key}`) records the expected specs of the callees it "
        "depends on in its [INFO] block. Update that block so its entry for the callee is "
        "CONSISTENT with the callee's new spec — it need NOT be identical, it only must not "
        "conflict (no contradictory pre/post-conditions). Leave the entries for every other "
        "callee unchanged.\n\n"
        f"Comment prefix for this language: `{comment_prefix}`.\n\n"
        f"{knowledge_section}"
        "## Callee's updated [SPEC] block\n\n"
        f"{callee_new_spec}\n\n"
        "## Caller's current source\n\n"
        f"```{lang_key}\n{caller_source.strip()}\n```\n\n"
        "## Caller's current [INFO] block (the expected specs of its callees)\n\n"
        f"{caller_info_block}\n\n"
        "## Steps\n\n"
        f"1. Decide whether the caller's [INFO] entry for `{callee_name}` already is consistent "
        "with the callee's new spec. If it is, no update is needed.\n"
        f"2. If it conflicts, produce the COMPLETE replacement [INFO] block (the `[INFO]` ... "
        f"`[INFO]` block only, markers included, every line prefixed with `{comment_prefix}`), "
        f"adjusting only the `{callee_name}` entry to be consistent and leaving the other "
        "entries as-is.\n"
        "3. Return ONLY a JSON object with keys:\n"
        '   - "info_updated": boolean.\n'
        '   - "new_info": string — the full replacement [INFO] block, or "" if not updated.\n'
        "   Do not include Markdown, tags, or prose outside the JSON object.\n"
    )

    return _llm_select_json(
        work_dir,
        prompt_content,
        stage="update_caller_info",
        validator=_validate_caller_info_update,
        schema_description='{"info_updated": boolean, "new_info": string}',
        trace_meta={"caller_fqn": caller_fqn, "callee_name": callee_name, "idx": idx},
    )
