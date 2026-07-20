# [SPEC]
# Unit: src/incremental_reasoner-py/_llm_check_spec_update.py
#
# _llm_check_spec_update(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
#                        developer_intent, spec_block, info_block, callee_names, source)
#   -> dict | None
#
# Pre-condition:
#   - proj_dir and work_dir are valid directory paths on disk
#   - idx is a non-negative integer used only for trace-event labeling
#   - fqn is a non-empty fully-qualified function name string
#   - lang_key is a valid language identifier for which comment_prefix is the
#     single-line comment marker
#   - comment_prefix is the single-line comment prefix for the source language
#   - developer_intent is a non-empty string describing the goal of the code
#     modification being analyzed
#   - spec_block is either None (no existing spec) or a non-empty string
#     containing the function's current [SPEC] block including its opening and
#     closing marker lines
#   - info_block is either None (no existing info block) or a non-empty string
#     containing the function's current [INFO] block including its marker lines
#   - callee_names is a list of non-empty strings naming the function's known
#     callees; the list may be empty
#   - source is a non-empty string containing the function's complete source
#     code, inclusive of any leading [SPEC] and [INFO] comment blocks
#
# Post-condition:
#   - Constructs an LLM prompt that presents: the developer intent, the
#     function's current source code, its existing [SPEC] block (or an
#     indication that none exists), its current [INFO] block with callee
#     relationship hints (or an indication that none exists), and the list of
#     known callee names
#   - The prompt asks the LLM to decide whether the [SPEC] block must be updated
#     to correctly describe the function's behavior after the intended
#     modification, and if so, whether the [INFO] block must also be updated to
#     reflect the new spec and any changes to the callee set
#   - Sends the prompt to an LLM and validates the response against a JSON
#     schema requiring keys: "spec_updated" (bool), "new_spec" (string),
#     "info_updated" (bool), "new_info" (string), "updated_callees" (list of
#     strings)
#   - When the LLM returns valid, parseable JSON, spec_updated is True if and
#     only if the [SPEC] block requires modification to remain a correct
#     behavioral specification after the intended change; when True, new_spec
#     contains the complete replacement [SPEC] block (markers included); when
#     False, new_spec is the empty string
#   - info_updated is True if and only if the [INFO] block was modified as a
#     consequence of the spec update or a change in the callee set, including
#     any of: adding entries for new callees, dropping entries for callees no
#     longer called, or revising entries whose expected spec contradicts the new
#     [SPEC]; when True, new_info contains the complete replacement [INFO] block
#     (markers included); when False, new_info is the empty string
#   - updated_callees is a list of callee name strings whose expected spec entry
#     was added or changed in the new [INFO] block; the list is empty when no
#     callee entries were affected or when info_updated is False
#   - Returns None when the LLM produces no response, or when the response
#     cannot be parsed as valid JSON matching the required schema
#   - Domain knowledge files from under work_dir, if any exist at the expected
#     location, are included in the prompt as additional context
#   - The function performs no file writes and does not modify source
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

def _llm_check_spec_update(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
                           developer_intent, spec_block, info_block, callee_names, source):
    """
    Ask the LLM whether a function's [SPEC] (and, if so, its [INFO]) block must change to
    reflect developer_intent, and return the parsed decision.

    The prompt inlines the entire function source, its current [SPEC]/[INFO] blocks, and the
    developer intent, so it needs no repository file access and is issued as a direct LLM
    call (via _llm_select_json) rather than an opencode run. idx is used only to label the
    traced exchange.

    Returns the parsed result dict — keys: "spec_updated" (bool), "new_spec" (str),
    "info_updated" (bool), "new_info" (str), "updated_callees" (list[str]) — or None when
    the LLM produced nothing usable.
    """
    callee_hint = ", ".join(sorted(callee_names)) if callee_names else "(none)"
    if not callee_names:
        info_section = "This function has no callees, so there is no [INFO] block to maintain.\n\n"
    elif info_block is not None:
        info_section = (
            "## Current [INFO] block (the expected specs of the callees this function depends on)\n\n"
            f"{info_block}\n\n"
            "NOTE: a modification may have changed which callees this function calls, so this "
            f"block may be missing entries for some current callees ({callee_hint}) or contain "
            "entries for callees no longer called.\n\n"
        )
    else:
        info_section = (
            "This function currently has no [INFO] block, but a modification may have made it "
            f"call other functions, so it now has callees ({callee_hint}); a new [INFO] block "
            "may need to be created for them.\n\n"
        )

    knowledge_section = _domain_knowledge_prompt_section(work_dir)

    prompt_content = (
        "# Update Function Specification\n\n"
        "A modification is being applied to a codebase to achieve the developer intent "
        "below. Decide whether this function's behavioral specification must change to "
        "reflect that intent.\n\n"
        f"- Function fully-qualified name: `{fqn}` (language: `{lang_key}`).\n"
        f"- Comment prefix for this language: `{comment_prefix}`.\n"
        f"- Known callees of this function: {callee_hint}.\n\n"
        "## Developer intent\n\n"
        f"{developer_intent}\n\n"
        f"{knowledge_section}"
        "## Current function source\n\n"
        f"```{lang_key}\n{source.strip()}\n```\n\n"
        "## Current [SPEC] block (this function's own behavioral specification)\n\n"
        f"{spec_block}\n\n"
        f"{info_section}"
        "## Steps\n\n"
        "1. Decide whether the [SPEC] block still correctly and completely describes the "
        "function's behavior after the intended modification. If it remains correct, no "
        "update is needed.\n"
        "2. If it must change, produce the COMPLETE replacement [SPEC] block — the "
        "`[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with "
        f"`{comment_prefix}`, and NO source code.\n"
        "3. ONLY if you updated the [SPEC] block AND this function has callees: bring the "
        f"[INFO] block into line with this function's CURRENT callees ({callee_hint}). That "
        "means: (a) keep entries whose recorded expectation still matches the callee's role, "
        "(b) ADD an entry for any current callee not yet recorded (e.g. one the modification "
        "introduced), (c) DROP entries for callees this function no longer calls, and (d) "
        "revise any entry whose expected spec must change as a consequence of the new [SPEC]. "
        "If any of (a)-(d) changes the block, produce the COMPLETE replacement [INFO] block "
        f"(the `[INFO]` ... `[INFO]` block only, markers included, lines prefixed with "
        f"`{comment_prefix}`) and list the names of the callees whose expected spec you added "
        "or changed.\n"
        "4. Return ONLY a JSON object with keys:\n"
        '   - "spec_updated": boolean.\n'
        '   - "new_spec": string — the full replacement [SPEC] block, or "" if not updated.\n'
        '   - "info_updated": boolean — true when you produced a new/replacement [INFO] block.\n'
        '   - "new_info": string — the full replacement [INFO] block, or "" if not updated.\n'
        '   - "updated_callees": array of callee name strings whose expected spec you added or changed, or [].\n'
        "   Do not include Markdown, tags, or prose outside the JSON object.\n"
    )

    return _llm_select_json(
        work_dir,
        prompt_content,
        stage="update_function_spec",
        validator=_validate_spec_update,
        schema_description=(
            '{"spec_updated": boolean, "new_spec": string, "info_updated": boolean, '
            '"new_info": string, "updated_callees": [string]}'
        ),
        trace_meta={"fqn": fqn, "idx": idx},
    )
