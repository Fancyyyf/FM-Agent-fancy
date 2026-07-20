# [SPEC]
# Unit: main.py
#
# run_pipeline(proj_dir, resume, required_source_files, domain_knowledge_files, submodules, one_phase, extra_call_edges_path, only_spec) -> None
#
# Pre-condition:
#   - proj_dir is a non-None string; if it does not reference an existing directory, the function prints a diagnostic and calls sys.exit(1)
#   - If proj_dir is a directory but contains no files with an extension recognized by the pipeline, the function prints a diagnostic and calls sys.exit(1)
#   - resume is a truthy/falsy value; when truthy and fm_agent/ exists under proj_dir, previously completed pipeline work is preserved and only remaining work executes
#   - domain_knowledge_files is None or an iterable of path strings pointing to existing markdown files
#   - submodules is None or a non-empty iterable of subdirectory names relative to proj_dir; when provided, only those subdirectories are processed
#   - one_phase is a truthy/falsy value
#   - extra_call_edges_path is None or a path to a JSON file defining supplemental call-graph edges in the format specified by engine conventions
#   - only_spec is a truthy/falsy value
#
# Post-condition:
#   - On success (normal return): the full pipeline has executed across all source files under proj_dir
#   - If only_spec is truthy: every function in the extracted call graph has a behavioral spec ([SPEC] block) prepended to its extracted-function file; no verification or bug validation runs
#   - If only_spec is falsy: specs are generated, then each specced function has a verification result in fm_agent/logic_verification_results/, and each MISMATCH has a bug validation report in fm_agent/bug_validation/
#   - The fm_agent/ work directory under proj_dir is created and populated; no file outside fm_agent/ under proj_dir is modified
#   - If resume is truthy and fm_agent/ exists, previously completed stages are not re-executed; if resume is falsy or fm_agent/ is absent, all prior fm_agent/ contents are removed before starting
#   - User domain knowledge files are staged into fm_agent/spec_prompts/domain_context/user_knowledge/ before any pipeline stage executes
#   - If no functions are found for verification (empty file_list), the function returns early without generating specs
#   - On unrecoverable stage failure after all configured retries: prints a diagnostic identifying the failed stage and the trace directory, then calls sys.exit(1)
#   - Pipeline stages execute sequentially: phases.json generation → domain context generation → function extraction → spec generation → (optionally) verification → bug validation
#   - The function outputs status messages to stdout for each major stage transition
#   - In only_spec mode, the final summary does not print a confirmed-bug count
# [SPEC]

# [INFO]
# _has_source_code(proj_dir, submodules) -> bool
#   Pre-condition: proj_dir is a directory path; submodules is None or a list of subdirectory names
#   Post-condition: returns True if proj_dir (optionally scoped to submodules) contains at least one file whose extension matches a pipeline-supported language; returns False otherwise
# [SPLIT]
# stage_domain_knowledge_files(proj_dir, work_dir, markdown_paths) -> list[str]
#   Pre-condition: markdown_paths is None or a list of file paths
#   Post-condition: copies each existing markdown file into fm_agent/spec_prompts/domain_context/user_knowledge/ under work_dir; returns a list of project-relative paths for all staged files
# [SPLIT]
# _run_generate_phases(proj_dir, work_dir, script_dir, resume, submodules) -> None
#   Pre-condition: work_dir exists; script_dir is the directory containing the pipeline source
#   Post-condition: fm_agent/phases.json exists under work_dir with the phases.json schema; calls sys.exit(1) on unrecoverable failure
# [SPLIT]
# _post_process_phases(proj_dir, work_dir, required_source_files, submodules, one_phase) -> bool
#   Pre-condition: phases.json exists under work_dir
#   Post-condition: phases.json is updated: required files are ensured present, submodule filtering is applied, duplicates are removed, empty phases are cleaned, phase numbers are compacted; returns True if phases.json was modified, False otherwise
# [SPLIT]
# _run_generate_domain_context(proj_dir, work_dir, script_dir, resume) -> None
#   Pre-condition: phases.json exists under work_dir
#   Post-condition: engine_overview.txt and one phase_NN_types.txt per phase exist under spec_prompts/domain_context/; calls sys.exit(1) on unrecoverable failure
# [SPLIT]
# collect_file_names(input_dir, file_list_path) -> list[str]
#   Pre-condition: input_dir is the extracted_functions/ directory; file_list_path is a writable JSON path
#   Post-condition: returns the list of relative paths for all extracted function files; the list is cached at file_list_path and reused on subsequent calls
# [SPLIT]
# generate_topdown_layers(work_dir, extra_call_edges) -> None
#   Pre-condition: work_dir contains extracted_functions/; extra_call_edges is a dict of supplemental edges or None
#   Post-condition: one or more phase_NN_topdown_layers.json files exist under spec_prompts/, each ordering functions so that every callee is assigned to a layer lower than its callers (topological order)
# [SPLIT]
# is_file_ready(extracted_path) -> bool
#   Pre-condition: extracted_path references an existing extracted-function file
#   Post-condition: returns True if the file contains at least two lines matching [SPEC] and at least two lines matching [INFO]; returns False otherwise
# [SPLIT]
# streaming_reasoner(input_dir, output_dir, file_list, proj_dir, work_dir, spec_procs, already_processed, resume) -> set[str]
#   Pre-condition: input_dir contains extracted function files; file_list is a list of relative paths to functions to process
#   Post-condition: produces a verification result JSON for each processed function under output_dir; returns the set of function FQNs that were newly verified
# [SPLIT]
# _run_spec_generation_batch(proj_dir, work_dir, attempt, phase_num, layer_idx, batch_rel_dir, batch_info) -> None
#   Pre-condition: batch_info describes a batch prompt file and its target function paths; work_dir contains the workflow spec and system prompt
#   Post-condition: executes an OpenCode agent process to generate [SPEC] and [INFO] blocks for each function in the batch; updates the extracted function files in place
# [SPLIT]
# _clean_previous_run(work_dir) -> None
#   Pre-condition: work_dir is a path string
#   Post-condition: the work_dir directory tree is recursively removed if it exists
# [INFO]

def run_pipeline(
    proj_dir,
    resume=False,
    required_source_files=None,
    domain_knowledge_files=None,
    submodules=None,
    one_phase=False,
    extra_call_edges_path=None,
    only_spec=False,
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
    print("[Pipeline] Stage 1/6: Generating phase plan...")
    _run_generate_phases(
        proj_dir, work_dir, script_dir, resume=resume,
        submodules=submodules,
    )

    phases_modified = _post_process_phases(
        proj_dir, work_dir,
        required_source_files=required_source_files,
        submodules=submodules,
        one_phase=one_phase,
    )

    print("[Pipeline] Stage 2/6: Generating domain context...")
    _run_generate_domain_context(proj_dir, work_dir, script_dir, resume=resume and not phases_modified)

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
    batch_md_src = os.path.join(script_dir, "md", "workflow_spec_step4_batch.md")
    batch_md_dst = os.path.join(work_dir, "workflow_spec_step4_batch.md")
    shutil.copy2(batch_md_src, batch_md_dst)

    all_processed = set()
    num_phases = len(phases_data["phases"])
    project_name = phases_data.get("project", "project")

    for phase_info in sorted(phases_data["phases"], key=lambda p: p["phase"]):
        phase_num = phase_info["phase"]
        phase_name = phase_info["name"]
        phase_files = _get_phase_files(phases_data, phase_num, input_dir)

        if not phase_files:
            logging.info(f"Phase {phase_num} ({phase_name}): no extracted files, skipping.")
            continue

        # Determine how many layers this phase has
        layers_json_path = os.path.join(
            spec_prompts_dir, f"phase_{phase_num:02d}_topdown_layers.json"
        )
        if not os.path.exists(layers_json_path):
            generate_topdown_layers(work_dir, [phase_num], extra_call_edges=extra_call_edges)
        with open(layers_json_path, "r") as f:
            layers_data = json.load(f)
        total_layers = layers_data.get("total_layers", 1)

        batch_dir = os.path.join(
            spec_prompts_dir,
            f"batch_prompts_{project_name}_phase{phase_num:02d}",
        )

        for layer_idx in range(total_layers):
            print(f"[Pipeline] Stage 6/6: Phase {phase_num}/{num_phases} — {phase_name}, Layer {layer_idx}/{total_layers - 1}")

            # Generate batch prompts for this layer. On resume, skip functions
            # that were already specced in a previous run.
            batch_cmd = ["python3", "fm_agent/spec_prompts/generate_batch_prompts.py",
                         "--phase", str(phase_num), "--layers", str(layer_idx)]
            if resume:
                batch_cmd.append("--resume")
            subprocess.run(batch_cmd, cwd=proj_dir, check=True)

            # Read manifest
            manifest_path = os.path.join(batch_dir, "manifest.json")
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            all_batches = manifest.get("batches", [])

            if not all_batches:
                logging.info(f"Phase {phase_num} Layer {layer_idx}: no batches, skipping.")
                continue

            batch_rel_dir = os.path.relpath(batch_dir, proj_dir)

            # Build file list for this layer from the manifest
            layer_files = []
            for batch_info in all_batches:
                for func_rel in batch_info.get("functions", []):
                    rel = os.path.relpath(os.path.join(proj_dir, func_rel), input_dir)
                    layer_files.append(rel)

            layer_processed = set()

            for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
                # Find batches with unspecced functions
                pending_batches = _get_pending_batches(all_batches, proj_dir)
                if not pending_batches:
                    # All functions in this layer are specced. In only-spec mode
                    # we stop here without running the reasoner/bug validation.
                    if not only_spec:
                        incomplete_verification = _get_incomplete_verification_files(
                            layer_files, input_dir, output_dir, work_dir
                        )
                        if incomplete_verification:
                            logging.info(
                                f"Phase {phase_num} Layer {layer_idx}: "
                                f"{len(incomplete_verification)} ready file(s) still need verification or validation"
                            )
                            newly_processed = streaming_reasoner(
                                input_dir, output_dir, file_list=layer_files,
                                proj_dir=proj_dir, work_dir=work_dir,
                                spec_procs=None,
                                already_processed=all_processed | layer_processed,
                                resume=resume,
                            )
                            layer_processed.update(newly_processed)
                    break

                # Submit all pending spec batches through a bounded executor so
                # finished slots can immediately pick up the next batch.
                spec_futures = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    for batch_info in pending_batches:
                        batch_file = batch_info["file"]
                        batch_prompt_rel = os.path.join(batch_rel_dir, batch_file)
                        batch_prompt_abs = os.path.join(proj_dir, batch_prompt_rel)
                        # On resume a batch whose functions are all already specced
                        # has no prompt file written and nothing for the agent to do
                        # — skip it instead of sending an empty batch.
                        if batch_info.get("num_pending", 1) == 0 or not os.path.exists(batch_prompt_abs):
                            logging.info(f"Skipping batch with no functions to spec: {batch_file}")
                            continue
                        spec_futures.append(
                            executor.submit(
                                _run_spec_generation_batch,
                                proj_dir,
                                work_dir,
                                attempt,
                                phase_num,
                                layer_idx,
                                batch_rel_dir,
                                batch_info,
                            )
                        )

                    logging.info(
                        f"Phase {phase_num} Layer {layer_idx} attempt {attempt}: "
                        f"submitted {len(spec_futures)} spec-generation batch tasks "
                        f"(max_workers={MAX_WORKERS}, total_pending_batches={len(pending_batches)})"
                    )
                    if spec_futures and not only_spec:
                        newly_processed = streaming_reasoner(
                            input_dir, output_dir, file_list=layer_files,
                            proj_dir=proj_dir, work_dir=work_dir,
                            spec_procs=spec_futures,
                            already_processed=all_processed | layer_processed,
                            resume=resume,
                        )
                        layer_processed.update(newly_processed)

                    for future in spec_futures:
                        try:
                            future.result()
                        except Exception as exc:
                            logging.error(f"Spec generation task failed unexpectedly: {exc}")

                # Check if any files in this layer received specs
                specs_generated = sum(
                    1 for rel in layer_files
                    if is_file_ready(os.path.join(input_dir, rel))
                )
                if specs_generated > 0 and not _get_pending_batches(all_batches, proj_dir):
                    break

                if specs_generated > 0:
                    # Partial progress — retry remaining batches without delay
                    logging.info(
                        f"Phase {phase_num} Layer {layer_idx} attempt {attempt}: "
                        f"{specs_generated} specs generated, retrying remaining batches"
                    )
                    continue

                if attempt < OPENCODE_MAX_RETRIES:
                    delay = 10
                    print(
                        f"[Pipeline] Stage 6 Phase {phase_num} Layer {layer_idx} produced no specs "
                        f"(attempt {attempt}/{OPENCODE_MAX_RETRIES}). "
                        f"Retrying in {delay}s..."
                    )
                    logging.warning(
                        f"Stage 6 Phase {phase_num} Layer {layer_idx} attempt {attempt} failed: "
                        f"no specs generated. Retrying in {delay}s."
                    )
                    time.sleep(delay)
                else:
                    print(
                        f"[Pipeline] ERROR: Stage 6 Phase {phase_num} Layer {layer_idx} failed "
                        f"after {OPENCODE_MAX_RETRIES} attempts. "
                        f"No specs were generated. "
                        f"Check {os.path.basename(proj_dir)}/fm_agent/trace/ for details."
                    )
                    sys.exit(1)

        # Mark all files from this phase as processed for subsequent phases
        for rel in phase_files:
            all_processed.add(os.path.join(input_dir, rel))

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
