def _llm_check_caller_info_update(proj_dir, work_dir, idx, caller_fqn, callee_name,
                                  lang_key, comment_prefix, callee_new_spec,
                                  caller_info_block, caller_source):
    """
    Ask whether a caller's .info.json must change to stay consistent with a callee whose
    .spec.json was just updated.

    The caller's .info.json records the expected specs of the callees it depends on. This
    asks the model to reconcile only the entry for callee_name with the callee's new spec —
    consistency, not equality: the entry must merely not conflict with the new spec, and the
    entries for other callees are left untouched. The prompt inlines the callee's new spec
    and the caller's source/info sidecar, so it is issued as a direct LLM call (via
    _llm_select_json) rather than an opencode run; idx only labels the traced exchange.

    Returns the parsed result dict — keys "info_updated" (bool) and "new_info" (dict) — or
    None when the LLM produced nothing usable.
    """
    knowledge_section = _domain_knowledge_prompt_section(work_dir)

    prompt_content = (
        "# Reconcile a Caller's .info.json with a Changed Callee\n\n"
        f"The callee `{callee_name}`'s behavioral specification was just updated. The caller "
        f"`{caller_fqn}` (language `{lang_key}`) records the expected specs of the callees it "
        "depends on in its .info.json. Update that object so its entry for the callee is "
        "CONSISTENT with the callee's new spec — it need NOT be identical, it only must not "
        "conflict (no contradictory pre/post-conditions). Leave the entries for every other "
        "callee unchanged.\n\n"
        f"{knowledge_section}"
        "## Callee's updated .spec.json\n\n"
        f"```json\n{json.dumps(callee_new_spec, indent=2, ensure_ascii=False)}\n```\n\n"
        "## Caller's current source\n\n"
        f"```{lang_key}\n{caller_source.strip()}\n```\n\n"
        "## Caller's current .info.json (the expected specs of its callees)\n\n"
        f"```json\n{json.dumps(caller_info_block, indent=2, ensure_ascii=False)}\n```\n\n"
        "## Steps\n\n"
        f"1. Decide whether the caller's .info.json entry for `{callee_name}` already is consistent "
        "with the callee's new spec. If it is, no update is needed.\n"
        "2. If it conflicts, produce the COMPLETE replacement .info.json object, "
        f"adjusting only the `{callee_name}` entry to be consistent and leaving the other "
        "entries as-is.\n"
        "3. Return ONLY a JSON object with keys:\n"
        '   - "info_updated": boolean.\n'
        '   - "new_info": object — the full replacement .info.json object, or null if not updated.\n'
        "   Do not include Markdown, tags, or prose outside the JSON object.\n"
    )

    return _llm_select_json(
        work_dir,
        prompt_content,
        stage="update_caller_info",
        validator=_validate_caller_info_update,
        schema_description='{"info_updated": boolean, "new_info": object|null}',
        trace_meta={"caller_fqn": caller_fqn, "callee_name": callee_name, "idx": idx},
    )
