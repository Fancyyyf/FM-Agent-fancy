def _llm_check_spec_update(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
                           developer_intent, spec_block, info_block, callee_names, source):
    """
    Ask the LLM whether a function's .spec.json (and, if so, its .info.json) must change to
    reflect developer_intent, and return the parsed decision.

    The prompt inlines the entire function source, its current metadata sidecars, and the
    developer intent, so it needs no repository file access and is issued as a direct LLM
    call (via _llm_select_json) rather than an opencode run. idx is used only to label the
    traced exchange.

    Returns the parsed result dict — keys: "spec_updated" (bool), "new_spec" (dict),
    "info_updated" (bool), "new_info" (dict), "updated_callees" (list[str]) — or None when
    the LLM produced nothing usable.
    """
    callee_hint = ", ".join(sorted(callee_names)) if callee_names else "(none)"
    if not callee_names:
        info_section = (
            "This function has no callees, so .info.json must contain "
            '{"callees": []}.\n\n'
        )
    elif info_block is not None:
        info_section = (
            "## Current .info.json (the expected specs of the callees this function depends on)\n\n"
            f"```json\n{json.dumps(info_block, indent=2, ensure_ascii=False)}\n```\n\n"
            "NOTE: a modification may have changed which callees this function calls, so this "
            f"object may be missing entries for some current callees ({callee_hint}) or contain "
            "entries for callees no longer called.\n\n"
        )
    else:
        info_section = (
            "This function currently has no .info.json, but a modification may have made it "
            f"call other functions, so it now has callees ({callee_hint}); a new .info.json "
            "may need to be created for them.\n\n"
        )

    knowledge_section = _domain_knowledge_prompt_section(work_dir)

    prompt_content = (
        "# Update Function Specification\n\n"
        "A modification is being applied to a codebase to achieve the developer intent "
        "below. Decide whether this function's behavioral specification must change to "
        "reflect that intent.\n\n"
        f"- Function fully-qualified name: `{fqn}` (language: `{lang_key}`).\n"
        f"- Known callees of this function: {callee_hint}.\n\n"
        "## Developer intent\n\n"
        f"{developer_intent}\n\n"
        f"{knowledge_section}"
        "## Current function source\n\n"
        f"```{lang_key}\n{source.strip()}\n```\n\n"
        "## Current .spec.json (this function's own behavioral specification)\n\n"
        f"```json\n{json.dumps(spec_block, indent=2, ensure_ascii=False)}\n```\n\n"
        f"{info_section}"
        "## Steps\n\n"
        "1. Decide whether .spec.json still correctly and completely describes the "
        "function's behavior after the intended modification. If it remains correct, no "
        "update is needed.\n"
        "2. If it must change, produce the COMPLETE replacement .spec.json object, with "
        "exactly signature, pre_condition, and post_condition, and NO source code.\n"
        "3. ONLY if you updated .spec.json AND this function has callees: bring "
        f".info.json into line with this function's CURRENT callees ({callee_hint}). That "
        "means: (a) keep entries whose recorded expectation still matches the callee's role, "
        "(b) ADD an entry for any current callee not yet recorded (e.g. one the modification "
        "introduced), (c) DROP entries for callees this function no longer calls, and (d) "
        "revise any entry whose expected spec must change as a consequence of the new spec. "
        "If any of (a)-(d) changes the object, produce the COMPLETE replacement .info.json "
        "object with exactly the callees field and list the names of the callees whose expected "
        "spec you added or changed.\n"
        "4. Return ONLY a JSON object with keys:\n"
        '   - "spec_updated": boolean.\n'
        '   - "new_spec": object — the full replacement .spec.json object, or null if not updated.\n'
        '   - "info_updated": boolean — true when you produced a new/replacement .info.json object.\n'
        '   - "new_info": object — the full replacement .info.json object, or null if not updated.\n'
        '   - "updated_callees": array of callee name strings whose expected spec you added or changed, or [].\n'
        "   Do not include Markdown, tags, or prose outside the JSON object.\n"
    )

    return _llm_select_json(
        work_dir,
        prompt_content,
        stage="update_function_spec",
        validator=_validate_spec_update,
        schema_description=(
            '{"spec_updated": boolean, "new_spec": object|null, "info_updated": boolean, '
            '"new_info": object|null, "updated_callees": [string]}'
        ),
        trace_meta={"fqn": fqn, "idx": idx},
    )
