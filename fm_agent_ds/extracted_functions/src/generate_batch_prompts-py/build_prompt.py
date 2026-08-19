def build_prompt(
    phase: int,
    layer_idx: int,
    is_cycle: bool,
    functions: List[dict],
    func_to_layer: Dict[str, int],
    all_funcs: Dict[str, dict],
    work_dir: Path,
    fm_agent_prefix: str,
    ext_to_lang: Dict[str, str],
) -> str:
    lines: List[str] = []
    sample_lang = "unknown"
    if functions:
        sample_lang, _ = detect_lang_and_comment(functions[0]["file"], ext_to_lang)

    lines.append(f"You are generating behavioral specifications for Phase {phase}, Layer {layer_idx}.")
    lines.append("")
    lines.append(
        f"Language: {sample_lang}. "
        "Write specifications to adjacent .spec.json and .info.json files."
    )
    lines.append("")
    lines.append(f"Read {fm_agent_prefix}spec_prompts/system_prompt.md FIRST for the mandatory spec format rules.")
    lines.append(f"Read: {fm_agent_prefix}spec_prompts/domain_context/engine_overview.txt")
    lines.append(f"Read: {fm_agent_prefix}spec_prompts/domain_context/phase_{phase:02d}_types.txt")
    user_knowledge_paths = list_staged_domain_knowledge_relpaths(
        work_dir,
        prefix=fm_agent_prefix.rstrip("/"),
    )
    if user_knowledge_paths:
        lines.append("Read these user-provided domain knowledge Markdown files:")
        for path in user_knowledge_paths:
            lines.append(f"- {path}")
    lines.append("")
    lines.append("## KEY RULES")
    lines.append("- Describe WHAT the function guarantees, NOT HOW it implements it")
    lines.append("- Do NOT name internal helper calls, loop structure, or data layout decisions")
    lines.append("- Do NOT enumerate members of sets - describe the GOVERNING RULE")
    lines.append("- Specs describe INTENDED CORRECT behavior per the domain (see domain files)")
    lines.append(f"- ALL files below exist in {fm_agent_prefix}extracted_functions/ - read and process each one")

    caller_specs: List[Tuple[str, str]] = []
    caller_expectations: Dict[str, List[Tuple[str, str]]] = {}
    for fn in functions:
        fn_name = fn["name"]
        caller_key = phase_callers_key(fn, phase)
        info_names_key = phase_callee_info_names_key(fn, phase)
        info_names_by_caller = fn.get(info_names_key, {}) if info_names_key else {}
        callers = fn.get(caller_key, [])
        for caller_name in callers:
            caller_layer = func_to_layer.get(caller_name)
            if caller_layer is None or caller_layer >= layer_idx:
                continue
            caller_meta = all_funcs.get(caller_name)
            if not caller_meta:
                continue
            caller_file = work_dir / caller_meta["file"]
            spec_block = extract_spec_block(caller_file)
            if spec_block and (caller_name, spec_block) not in caller_specs:
                caller_specs.append((caller_name, spec_block))
            info_dict = extract_info_block(caller_file)
            if not info_dict:
                continue
            entry = extract_callee_spec_from_info(
                info_dict, fn_name, info_names_by_caller.get(caller_name, [])
            )
            if entry:
                entry_text = (
                    f"{entry.get('signature', '')}\n"
                    f"  Pre-condition: {entry.get('pre_condition', '')}\n"
                    f"  Post-condition: {entry.get('post_condition', '')}"
                )
                caller_expectations.setdefault(fn_name, []).append(
                    (caller_name, entry_text)
                )

    if caller_specs:
        lines.append("")
        lines.append("## EARLIER-LAYER CALLER SPECS")
        for caller_name, block in caller_specs:
            lines.append(f"#### {caller_name}")
            lines.append("")
            lines.append(block)
            lines.append("")

    if caller_expectations:
        lines.append("## CALLEE EXPECTATIONS FROM CALLERS")
        for fn in functions:
            fn_name = fn["name"]
            entries = caller_expectations.get(fn_name, [])
            if not entries:
                continue
            lines.append(f"### What callers expect from {fn_name}:")
            for caller_name, entry in entries:
                lines.append(f"#### According to {caller_name}:")
                lines.append(entry)
            lines.append("")

    if is_cycle:
        lines.append("## CYCLE LAYER GUIDANCE")
        lines.append("These functions call each other (mutual recursion / circular dependencies).")
        lines.append(
            'Ask: "What is true after this function returns, regardless of which caller invoked it and which code path executed?" '
            "That invariant is your post-condition."
        )
        lines.append("")
        lines.append("DISPATCH FUNCTION TEST: If your spec has N bullets where N equals the number")
        lines.append("of switch arms / dispatch cases, you are transcribing the implementation.")
        lines.append("A dispatch function's contract is the invariant that holds ACROSS ALL cases.")
        lines.append("")

    lines.append(f"## FUNCTIONS ({len(functions)} total - process ALL)")
    for idx, fn in enumerate(functions, start=1):
        fn_name = fn["name"]
        caller_key = phase_callers_key(fn, phase)
        callers = fn.get(caller_key, [])
        earlier = [c for c in callers if func_to_layer.get(c, 10**9) < layer_idx]
        lines.append(f"### {idx}. {fm_agent_prefix}{fn['file']}")
        if earlier:
            lines.append("  Earlier-layer callers: " + ", ".join(earlier))
        else:
            lines.append("  Earlier-layer callers: (none)")

    lines.append("")
    lines.append("## SPEC FORMAT (write JSON files; do NOT modify source files)")
    lines.append("")
    lines.append(
        "For each function file `<function-file>`, "
        "write TWO JSON files in the SAME directory:"
    )
    lines.append("")
    lines.append("`<function-file>.spec.json`:")
    lines.append("```json")
    lines.append(
        '{"signature": "<FunctionName>(<params>) -> <ReturnType>", '
        '"pre_condition": "...", "post_condition": "..."}'
    )
    lines.append("```")
    lines.append("")
    lines.append("`<function-file>.info.json`:")
    lines.append("```json")
    lines.append(
        '{"callees": [{"name": "<callee_name>", "signature": "...", '
        '"pre_condition": "...", "post_condition": "..."}]}'
    )
    lines.append("```")
    lines.append("")
    lines.append('If the function has no callees: write `{"callees": []}` to the .info.json file.')
    lines.append("")
    lines.append("## PROCESS")
    lines.append("For each function:")
    lines.append("1. Read the extracted file")
    lines.append("2. Read caller expectations above - what do callers NEED from this function?")
    lines.append("3. Write a behavioral spec describing WHAT it guarantees (not HOW)")
    lines.append(
        "4. Write the COMPLETE .spec.json and .info.json objects next to the "
        "UNCHANGED source file"
    )
    lines.append("5. Use the Write tool to save both JSON files")
    return "\n".join(lines).rstrip() + "\n"
