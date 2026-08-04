def _sync_domain_context(proj_dir, work_dir, changed_phases, phase_cleanup=None):
    """Re-generate the per-phase domain-context files for phases whose source-file
    composition changed after phase edits.

    The phase-planning steps can force extra source files into an existing phase
    (see ``_ensure_source_files_in_phases``) or strip duplicate files from it (see
    ``_deduplicate_phases``). The generated
    ``spec_prompts/domain_context/phase_NN_types.txt`` files are keyed by phase
    number and their prose references phases/structs by meaning, so realigning a
    phase's types file with its new source-file set is semantic work. Rather than
    editing the text mechanically (which can be wrong), we hand the agent the exact
    set of changed phases and let it regenerate their types files from scratch
    against the freshly written phases.json.

    ``changed_phases`` is the set from ``_collect_changed_phases``. Only phases that
    still own at least one source file are regenerated — a phase left with an empty
    file list (e.g. all its files deduplicated away) has no types to describe. An
    empty set, or no changed phase with files, skips the agent call entirely.
    """
    phase_cleanup = phase_cleanup or {}
    removed_phases = [
        p for p in phase_cleanup.get("removed_phases", [])
        if p is not None
    ]
    renumbered = phase_cleanup.get("renumbered", {})
    cleanup_changed = bool(removed_phases) or any(
        old is not None and new is not None and old != new
        for old, new in renumbered.items()
    )
    if not changed_phases and not cleanup_changed:
        return
    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    if not os.path.isdir(domain_dir):
        logging.info("No domain_context/ directory to sync after phase edits; skipping.")
        return

    source_files_by_phase = _phase_source_files(os.path.join(work_dir, "phases.json"))
    regenerate = {
        phase_num: source_files_by_phase[phase_num]
        for phase_num in changed_phases
        if source_files_by_phase.get(phase_num)
    }
    if not regenerate and not cleanup_changed:
        logging.info(
            "No changed phase still owns source files; skipping domain-context regen."
        )
        return

    prompt = _build_domain_context_regen_prompt(regenerate, phase_cleanup)
    fm_reminder = ("IMPORTANT: fm_agent/ is your output workspace, not project source. "
                   "Do NOT modify any existing project files.")
    prompt = f"{prompt}\n\n{fm_reminder}"

    command = build_llm_cli_command(
        model=OPENCODE_SETUP_MODEL,
        prompt=prompt,
        cwd=proj_dir,
    )

    for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
        try:
            run_opencode_traced(
                proj_dir=proj_dir,
                work_dir=work_dir,
                command=command,
                stage="sync_domain_context",
                input_files=[
                    "fm_agent/phases.json",
                    *list_staged_domain_knowledge_relpaths(work_dir),
                ],
                output_files=[
                    "fm_agent/spec_prompts/domain_context/engine_overview.txt",
                ],
                summary=f"Regenerate domain_context for changed phases (attempt {attempt})",
                metadata={"attempt": attempt},
            )
            return
        except subprocess.CalledProcessError as e:
            logging.warning(
                "Domain-context sync attempt %d/%d failed: opencode exited %s",
                attempt, OPENCODE_MAX_RETRIES, e.returncode,
            )
            if attempt < OPENCODE_MAX_RETRIES:
                time.sleep(10)

    # The caller performs a final completeness check after this best-effort
    # sync, so warn here and let that single validation point decide whether the
    # pipeline can continue.
    logging.warning(
        "Domain-context sync did not complete after %d attempts; "
        "phase_NN_types.txt files may be out of sync with phases.json.",
        OPENCODE_MAX_RETRIES,
    )
