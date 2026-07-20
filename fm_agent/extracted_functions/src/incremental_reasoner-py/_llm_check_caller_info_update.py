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
