def _run_entry_pipeline_inner(
    proj_dir,
    work_dir,
    entry_func,
    end_funcs,
    resume,
    domain_knowledge_files=None,
    one_phase=False,
    extra_call_edges_path=None,
    only_spec=False,
    bug_validator_path=None,
    plugin_config=None,
):
    """Body of run_entry_pipeline; runs with the entry source file exempted."""
    # 1. Selection: extract fresh into a temp workspace and build the call graph.
    extra_call_edges = load_call_edges(extra_call_edges_path)
    all_by_source, keep_by_source = _select_functions_by_source(
        proj_dir,
        entry_func,
        end_funcs,
        extra_call_edges=extra_call_edges,
    )

    # 2. Copy the sources into a separate run directory, then trim that copy.
    # proj_dir is left untouched throughout.
    run_dir = proj_dir + ".fm-entry-run"
    run_work_dir = os.path.join(run_dir, "fm_agent")
    # _make_run_copy brings along an existing fm_agent/, so a resumed run finds
    # the prior state in run_dir without any extra seeding here.
    _make_run_copy(proj_dir, run_dir)
    try:
        # Build the codegraph index on the run copy before trimming so that
        # _trim_project_in_place detects function names/spans with the same
        # codegraph backend that _select_functions_by_source used to produce
        # keep_by_source. Without it the trim would fall back to the regex
        # extractor and could disagree with the selection (mismatched names or
        # spans -> wrong functions kept/removed). Non-fatal: skips silently if
        # codegraph is not installed (selection then also used regex, so the two
        # stay consistent). run_pipeline rebuilds the index again after the trim
        # edits these sources, so extraction sees the trimmed tree, not this one.
        try_codegraph_init(run_dir)
        _trim_project_in_place(run_dir, all_by_source, keep_by_source)

        # 3. Run the standard pipeline directly on the run copy.
        # Imported lazily to avoid a circular import (main imports
        # run_entry_pipeline at module load).
        from main import run_pipeline

        # Force the entry point's source file into phases.json even if the setup
        # agent omits it (e.g. because it looks like a test), so run_pipeline
        # always extracts and reasons about the entry function.
        run_pipeline(
            run_dir,
            resume=resume,
            required_source_files=[_entry_func_source_rel(entry_func)],
            domain_knowledge_files=domain_knowledge_files,
            one_phase=one_phase,
            extra_call_edges_path=extra_call_edges_path,
            only_spec=only_spec,
            bug_validator_path=bug_validator_path,
            plugin_config=plugin_config,
        )
    finally:
        # 4. Copy the generated fm_agent/ back into proj_dir, then discard the
        # run directory. Runs even on failure so partial results are preserved.
        if os.path.isdir(run_work_dir):
            if os.path.isdir(work_dir):
                shutil.rmtree(work_dir)
            shutil.copytree(run_work_dir, work_dir, symlinks=True)
            print(f"[EntryPipeline] Copied generated fm_agent/ to {work_dir}.")
        shutil.rmtree(run_dir, ignore_errors=True)

    # Report the bug count: the number of MISMATCH verdicts the reasoner wrote
    # into fm_agent/logic_verification_results/.
    mismatches = _count_mismatches(os.path.join(work_dir, "logic_verification_results"))
    print(f"[EntryPipeline] Bugs (mismatches): {mismatches}")

    print(f"[EntryPipeline] Done. Results in {work_dir}.")
