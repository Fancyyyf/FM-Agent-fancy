def _run_setup_extract(proj_dir, work_dir, script_dir, is_incremental=False,
                       resume=False, required_source_files=None,
                       submodules=None, one_phase=False,
                       plugin_config=None):
    """Run generate-phases, post-process, and generate-domain-context stages.

    Backward-compatible wrapper that calls the three sub-stages in sequence.
    """
    phase_stage = plugin_config.get_stage("generate_phase_plan") if plugin_config else None
    context_stage = plugin_config.get_stage("generate_domain_context") if plugin_config else None
    plugin_root = plugin_config.root if plugin_config else None

    _run_generate_phases(proj_dir, work_dir, script_dir, is_incremental, resume, submodules,
                         plugin_stage=phase_stage, plugin_root=plugin_root)
    phases_modified = _post_process_phases(proj_dir, work_dir, required_source_files, submodules, one_phase=one_phase)
    _run_generate_domain_context(proj_dir, work_dir, script_dir, resume and not phases_modified,
                                 plugin_stage=context_stage, plugin_root=plugin_root)

    if not _setup_outputs_complete(work_dir):
        print(
            "[Pipeline] ERROR: Stage 1/2 outputs are incomplete after "
            "post-processing. Expected fm_agent/phases.json, "
            "fm_agent/spec_prompts/domain_context/engine_overview.txt, and one "
            "phase_NN_types.txt per phase."
        )
        sys.exit(1)
