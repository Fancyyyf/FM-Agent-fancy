def run_pipeline(
    proj_dir,
    resume=False,
    required_source_files=None,
    domain_knowledge_files=None,
    submodules=None,
    one_phase=False,
    extra_call_edges_path=None,
    only_spec=False,
    bug_validator_path=None,
    plugin_config=None,
):
    if not os.path.isdir(proj_dir):
        print(f"[Pipeline] ERROR: proj_dir does not exist or is not a directory: {proj_dir}")
        sys.exit(1)
    if not _has_source_code(proj_dir, submodules):
        scope = f" selected submodule(s): {', '.join(submodules)}" if submodules else f" {proj_dir}"
        print(f"[Pipeline] ERROR: No source code files found in{scope}. "
              f"Supported extensions: {', '.join(sorted(EXT_TO_LANG.keys()))}")
        sys.exit(1)

    work_dir = os.path.join(proj_dir, "fm_agent")
    input_dir = os.path.join(work_dir, "extracted_functions")
    output_dir = os.path.join(work_dir, "logic_verification_results")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    extra_call_edges = load_call_edges(extra_call_edges_path)

    # Clean files from the previous run — unless resuming, where we keep all
    # prior progress (phases.json, generated specs, verification results) and
    # only do the remaining work.
    if resume:
        if os.path.isdir(work_dir):
            print(f"[Pipeline] RESUME: keeping existing {os.path.relpath(work_dir, proj_dir)}/ — only remaining work will run.")
        else:
            print("[Pipeline] RESUME requested but no previous fm_agent/ found — starting fresh.")
            resume = False
    else:
        _clean_previous_run(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    domain_knowledge_relpaths = stage_domain_knowledge_files(
        proj_dir, work_dir, domain_knowledge_files
    )
    if domain_knowledge_relpaths:
        print(
            "[Pipeline] User domain knowledge: "
            f"{len(domain_knowledge_relpaths)} markdown file(s)."
        )

    # Stage 1: generate phase.json (input: target code → phases.json)
    # Stage 2: generate domain context (input: phases.json → domain context files)
    phase_stage = plugin_config.get_stage("generate_phase_plan") if plugin_config else None
    context_stage = plugin_config.get_stage("generate_domain_context") if plugin_config else None
    plugin_root = plugin_config.root if plugin_config else None

    print("[Pipeline] Stage 1/6: Generating phase plan...")
    _run_generate_phases(
        proj_dir, work_dir, script_dir, resume=resume,
        submodules=submodules,
        plugin_stage=phase_stage,
        plugin_root=plugin_root,
    )

    phases_modified = _post_process_phases(
        proj_dir, work_dir,
        required_source_files=required_source_files,
        submodules=submodules,
        one_phase=one_phase,
    )

    print("[Pipeline] Stage 2/6: Generating domain context...")
    _run_generate_domain_context(
        proj_dir,
        work_dir,
        script_dir,
        resume=resume and not phases_modified,
        plugin_stage=context_stage,
        plugin_root=plugin_root,
    )

    # Build (or rebuild) the codegraph index if codegraph is installed. Both
    # run_extraction (Stage 3) and generate_topdown_layers (Stage 5) read from it.
    # force=not resume mirrors run_extraction below: a fresh run rebuilds so the
    # index matches the current tree, while a resume reuses the existing index
    # (same tree as the interrupted run — rebuilding would just be wasted work).
    try_codegraph_init(proj_dir, force=not resume)

    # Run function extraction using extract.py
    # force=False on resume preserves already-specced extracted files; on a fresh
    # run fm_agent/ was just wiped so it is equivalent to force=True.
    print("[Pipeline] Stage 3/6: Extracting functions from source files...")
    run_extraction(proj_dir, work_dir=work_dir, force=not resume, verbose=True)

    # Copy system_prompt.md to spec_prompts/system_prompt.md
    spec_prompts_dir = os.path.join(work_dir, "spec_prompts")
    os.makedirs(spec_prompts_dir, exist_ok=True)
    shutil.copy2(
        os.path.join(script_dir, "md", "system_prompt.md"),
        os.path.join(spec_prompts_dir, "system_prompt.md"),
    )
    shutil.copy2(
        os.path.join(script_dir, "src", "generate_batch_prompts.py"),
        os.path.join(spec_prompts_dir, "generate_batch_prompts.py"),
    )
    # generate_batch_prompts.py imports is_file_ready from this module at runtime.
    shutil.copy2(
        os.path.join(script_dir, "src", "file_utils.py"),
        os.path.join(spec_prompts_dir, "file_utils.py"),
    )

    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path, "r") as f:
        phases_data = json.load(f)

    print("[Pipeline] Stage 4/6: Collecting file list...")
    file_list_path = os.path.join(work_dir, "fm_agent_file_list.json")
    file_list = collect_file_names(input_dir, file_list_path)
    if submodules:
        file_list = _write_file_names(
            _get_all_phase_files(phases_data, input_dir), file_list_path
        )

    if not file_list:
        print("[Pipeline] No functions found to verify. Skipping spec generation.")
        return

    # --- Stage 5: Generate topdown layers ---
    print("[Pipeline] Stage 5/6: Generating topdown layers...")
    generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges)

    # --- Stage 6: Execute spec generation workflow (per phase, per layer) ---
    if only_spec:
        print("[Pipeline] Stage 6/6: Generating specs (reasoning & bug validation disabled)...")
    else:
        print("[Pipeline] Stage 6/6: Generating specs & verification...")
    run_spec_generation_and_verification(
        proj_dir,
        work_dir,
        input_dir,
        output_dir,
        script_dir,
        spec_prompts_dir,
        phases_data,
        resume=resume,
        extra_call_edges=extra_call_edges,
        only_spec=only_spec,
        bug_validator_path=bug_validator_path,
    )

    # Print confirmed bug count (skipped in only-spec mode, which runs no
    # reasoning or bug validation).
    if not only_spec:
        summary_path = os.path.join(work_dir, "bug_validation", "summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, "r") as f:
                summary = json.load(f)
            confirmed = summary.get("total_confirmed", 0)
            print(f"[Pipeline] Confirmed bugs: {confirmed}")

    if only_spec:
        print("[Pipeline] Done (specs only; reasoning & bug validation skipped).")
    else:
        print("[Pipeline] Done.")
