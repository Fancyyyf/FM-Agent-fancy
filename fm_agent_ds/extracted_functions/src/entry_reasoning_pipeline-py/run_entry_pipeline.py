def run_entry_pipeline(
    proj_dir,
    entry_func=None,
    end_funcs=None,
    resume=False,
    domain_knowledge_files=None,
    one_phase=False,
    extra_call_edges_path=None,
    only_spec=False,
    bug_validator_path=None,
    plugin_config=None,
):
    """Run the entry-point-scoped reasoning pipeline.

    Algorithm:
      1. Collect the functions related to ``entry_func`` — those reachable from
         it, optionally restricted to call chains ending at ``end_funcs`` — by
         freshly extracting every function into a temporary workspace and
         building the static call graph. No previous run_pipeline() is assumed.
      2. Copy the project's sources into a separate run directory, then delete
         the unrelated functions and source files from that copy. ``proj_dir``
         itself is never modified.
      3. Invoke the standard ``run_pipeline`` directly on the run directory:
         because only the related functions remain, it naturally specs, reasons
         about, and bug-validates exactly that set, writing results to
         ``<run_dir>/fm_agent/``.
      4. Copy the generated ``fm_agent/`` workspace back into ``proj_dir`` and
         discard the run directory. The copy-back runs even when the pipeline
         fails, so partial results are preserved, and any stray edits the
         pipeline's agents made stay confined to the discarded run directory.

    The run directory lives beside the project at ``<proj_dir>.fm-entry-run``
    while the pipeline runs and is removed afterwards; a leftover one from an
    interrupted run is discarded and remade, since the pristine sources always
    remain in ``proj_dir``.

    Args:
        proj_dir: path to the project directory.
        entry_func: FQN of the entry point to start reasoning from.
        end_funcs: list of FQNs at which to stop. If None (or empty), no chain
            restriction is applied and the whole call graph reachable from
            ``entry_func`` is selected.
        resume: forwarded directly to the standard pipeline.
        one_phase: forwarded directly to the standard pipeline.
        extra_call_edges_path: optional file containing supplemental caller/callee
            edges used for entry reachability and later top-down layer generation.
    """
    if entry_func is None:
        raise ValueError("entry_func is required to run the entry pipeline")

    proj_dir = os.path.abspath(proj_dir)
    work_dir = os.path.join(proj_dir, "fm_agent")
    config.BUG_VALIDATION_MAX_RETRIES = 0

    # The entry_func's source file may match the test-file heuristics (a test
    # directory or test-like name). Exempt it so neither the selection extraction
    # below nor run_pipeline's extraction skips it — the entry point must always
    # be reasoned about. Cleared in the finally so the exemption never leaks into
    # a later run in the same process.
    add_test_file_exemption(_entry_func_source_rel(entry_func))
    try:
        _run_entry_pipeline_inner(
            proj_dir,
            work_dir,
            entry_func,
            end_funcs,
            resume,
            domain_knowledge_files=domain_knowledge_files,
            one_phase=one_phase,
            extra_call_edges_path=extra_call_edges_path,
            only_spec=only_spec,
            bug_validator_path=bug_validator_path,
            plugin_config=plugin_config,
        )
    finally:
        clear_test_file_exemptions()
