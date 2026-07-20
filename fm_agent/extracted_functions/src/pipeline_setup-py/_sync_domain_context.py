# [SPEC]
# Unit: src/pipeline_setup.py
#
# _sync_domain_context(proj_dir, work_dir, changed_phases, phase_cleanup=None) -> None
#
# Pre-condition:
#   - proj_dir is a path to an existing project directory.
#   - work_dir is a path to an existing fm_agent workspace directory.
#   - changed_phases is a collection of integer phase numbers, possibly empty.
#   - phase_cleanup, when provided, is a dict optionally containing key "removed_phases"
#     (list of integer phase numbers) and key "renumbered" (dict mapping old phase
#     number to new phase number, where both are non-None integers).
#   - phases.json must exist under work_dir and be valid per the phases.json schema
#     (each source file assigned to exactly one phase).
#
# Post-condition:
#   - Returns without effect when changed_phases is empty and no phase removal or
#     renumbering has occurred.
#   - Returns without invoking the LLM agent when the domain_context subdirectory
#     (spec_prompts/domain_context/) is absent under work_dir.
#   - Returns without invoking the LLM agent when every changed phase owns zero
#     source files per phases.json and no cleanup renumbering/removal is pending.
#   - When invoked, the LLM agent receives phases.json and all staged domain-knowledge
#     Markdown files as input and is instructed to regenerate phase_NN_types.txt
#     files only for phases whose source-file composition changed.
#   - The agent invocation is retried up to a configured maximum (OPENCODE_MAX_RETRIES),
#     with a delay between attempts. On success the function returns; after all
#     retries are exhausted, a warning is logged and the function returns without
#     raising — this is a best-effort operation.
#   - Every agent invocation is traced as an opencode_call event recorded in
#     fm_agent/trace/events.jsonl.
#   - The agent is constrained to write only under fm_agent/ and must not modify
#     any existing project source files.
# [SPEC]

# [INFO]
# _phase_source_files(json_path) -> dict[int, list[str]]
#   Pre-condition: json_path is a path to a valid phases.json file whose schema
#     conforms to the phases.json specification (array of phase objects, each with
#     a "phase" key and a "source_files" array).
#   Post-condition: returns a dict mapping each phase number (int) to its list of
#     source file paths (list of str), one entry per phase present in the file.
# [SPLIT]
# _build_domain_context_regen_prompt(regenerate, phase_cleanup) -> str
#   Pre-condition: regenerate is a non-empty dict mapping phase numbers to their
#     source file path lists; phase_cleanup is a dict optionally containing
#     "removed_phases" (list of int) and "renumbered" (dict of int → int).
#   Post-condition: returns a prompt string suitable for an LLM agent, instructing
#     it to regenerate phase_NN_types.txt domain-context files for the phases and
#     renumbering/removal changes described by the inputs.
# [SPLIT]
# build_llm_cli_command(model, prompt, cwd) -> list[str]
#   Pre-condition: model is a non-empty model identifier string; prompt is a
#     non-empty string; cwd is a path to an existing directory.
#   Post-condition: returns a command-line argument list that, when executed as a
#     subprocess, invokes the LLM with the given prompt in the specified working
#     directory. The returned list is non-empty.
# [SPLIT]
# run_opencode_traced(proj_dir, work_dir, command, stage, *, input_files, output_files, summary, metadata) -> None
#   Pre-condition: proj_dir and work_dir are paths to existing directories; command
#     is a non-empty list of strings; stage is a pipeline stage name; input_files
#     and output_files are optional lists of fm_agent-relative paths; summary is an
#     optional human-readable string; metadata is an optional dict.
#   Post-condition: on success, returns after the subprocess completes with exit
#     code 0 and a trace event is written to fm_agent/trace/events.jsonl. On
#     subprocess failure, raises subprocess.CalledProcessError; a trace event with
#     status "error" is written before the exception propagates.
# [SPLIT]
# list_staged_domain_knowledge_relpaths(work_dir) -> list[str]
#   Pre-condition: work_dir is a path to an existing fm_agent workspace directory
#     that may contain staged domain-knowledge files under
#     spec_prompts/domain_context/user_knowledge/.
#   Post-condition: returns a sorted list of project-relative file paths (using
#     "/" separators) for each domain-knowledge Markdown file staged under the
#     workspace. Returns an empty list when no files are staged.
# [INFO]

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
