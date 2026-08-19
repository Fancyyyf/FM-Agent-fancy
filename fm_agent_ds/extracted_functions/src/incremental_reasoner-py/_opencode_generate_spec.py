def _opencode_generate_spec(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
                            developer_intent, callee_names, source, caller_context):
    """
    Ask opencode to generate brand-new .spec.json and .info.json objects from scratch for a
    function that has no existing metadata sidecars — e.g. a function
    freshly added by the modification.

    Mirrors the full run's spec generation (run_pipeline Stage 6) but for a single function:
    opencode reads the project's spec format rules (fm_agent/spec_prompts/system_prompt.md),
    is given the same caller context the full run provides (each caller's .spec.json and what
    that caller's .info.json expects from this function, in caller_context as returned by
    _collect_caller_context), and produces the objects directly. Returns the parsed decision
    in the SAME shape as _opencode_check_spec_update so the caller can splice and propagate it
    identically.

    Returns the parsed result dict — keys: "spec_updated" (bool, true when .spec.json was
    produced), "new_spec" (dict), "info_updated" (bool), "new_info" (dict), "updated_callees"
    (list[str]) — or None when opencode produced nothing usable.
    """
    result_relpath = os.path.join("fm_agent", f"spec_generate_{idx}.json")
    prompt_relpath = os.path.join("fm_agent", f"spec_generate_{idx}.md")

    # Caller context (callers' own specs + what each caller's .info.json expects from this
    # function), mirroring run_pipeline's "EARLIER-LAYER CALLER SPECS" / "CALLEE EXPECTATIONS
    # FROM CALLERS" sections so the generated spec satisfies what callers depend on.
    caller_specs = [
        (cfqn, spec) for cfqn, spec, _ in caller_context if spec
    ]
    caller_expectations = [
        (cfqn, exp) for cfqn, _, exp in caller_context if exp
    ]
    caller_section = ""
    if caller_specs:
        caller_section += "## Specs of this function's callers\n\n"
        for cfqn, spec in caller_specs:
            caller_section += f"### {cfqn}\n\n{spec.strip()}\n\n"
    if caller_expectations:
        caller_section += (
            "## What callers expect from this function (from their .info.json files)\n\n"
            "Your generated .spec.json must be consistent with these expectations.\n\n"
        )
        for cfqn, exp in caller_expectations:
            caller_section += f"### According to {cfqn}\n\n{exp.strip()}\n\n"

    callee_hint = ", ".join(sorted(callee_names)) if callee_names else "(none)"
    user_knowledge_paths = list_staged_domain_knowledge_relpaths(work_dir)
    if user_knowledge_paths:
        user_knowledge_step = (
            "2. Read these user-provided domain knowledge Markdown files and use "
            "them as additional context:\n"
            f"{format_domain_knowledge_bullets(user_knowledge_paths)}\n"
        )
        step_offset = 1
    else:
        user_knowledge_step = ""
        step_offset = 0
    info_step_number = 3 + step_offset
    if callee_names:
        info_step = (
            f"{info_step_number}. Because this function has callees, also produce a .info.json "
            "object recording the expected behavioral spec of each callee it depends on, with "
            "exactly the callees field, and "
            "list the names of the callees you recorded.\n"
        )
    else:
        info_step = (
            f"{info_step_number}. This function has no callees, so produce a .info.json object "
            'with {"callees": []}.\n'
        )

    prompt_content = (
        "# Generate Function Specification\n\n"
        "A modification has been applied to a codebase to achieve the developer intent below, "
        "adding a function that has no behavioral specification yet. Generate its "
        "specification from scratch.\n\n"
        f"- Function fully-qualified name: `{fqn}` (language: `{lang_key}`).\n"
        f"- Known callees of this function: {callee_hint}.\n\n"
        "## Developer intent\n\n"
        f"{developer_intent}\n\n"
        "## Function source\n\n"
        f"```{lang_key}\n{source.strip()}\n```\n\n"
        f"{caller_section}"
        "## Steps\n\n"
        "1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact .spec.json/.info.json format "
        "rules used by this project.\n"
        f"{user_knowledge_step}"
        f"{2 + step_offset}. Produce the COMPLETE .spec.json object describing this "
        "function's behavior, with exactly signature, pre_condition, and post_condition, "
        "and NO source code.\n"
        f"{info_step}"
        f"{4 + step_offset}. Write your answer to `{result_relpath}` as a JSON object with keys:\n"
        '   - "spec_updated": boolean — true because you produced a .spec.json object.\n'
        '   - "new_spec": object — the full .spec.json object.\n'
        '   - "info_updated": boolean — true because you produced a .info.json object.\n'
        '   - "new_info": object — the full .info.json object.\n'
        '   - "updated_callees": array of callee name strings recorded in .info.json, or [].\n'
        "   Write ONLY that JSON file; do not modify any other project files.\n"
    )
    result = _opencode_select_json(
        proj_dir,
        work_dir,
        prompt_relpath,
        prompt_content,
        result_relpath,
        stage="generate_function_spec",
        input_files=[
            prompt_relpath,
            "fm_agent/spec_prompts/system_prompt.md",
            *user_knowledge_paths,
        ],
    )
    return _validate_spec_update(result) if result is not None else None
