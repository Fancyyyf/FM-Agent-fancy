# [SPEC]
# Unit: src/pipeline_setup.py
#
# _update_module_description(proj_dir, work_dir, modified_modules) -> None
#
# Pre-condition:
#   - proj_dir is a string path to the project root directory.
#   - work_dir is a string path to a writable fm_agent workspace directory.
#   - modified_modules is an iterable of module name strings (may be empty).
#
# Post-condition:
#   - When modified_modules is empty: returns immediately with no side effects.
#   - When phases.json does not exist under work_dir: logs an informational
#     message and returns with no side effects.
#   - When, after checking phases.json, none of the modules named in
#     modified_modules still owns any source file: logs an informational
#     message and returns with no side effects.
#   - Otherwise: delegates to an agent to rewrite the description field of
#     every module in modified_modules whose source file list in phases.json
#     differs from its pre-deduplication state. Each rewritten description
#     accurately reflects the module's current set of owned source files.
#   - The delegation is retried up to a configurable maximum number of
#     attempts. Between consecutive failed attempts, the function waits a
#     configurable fixed interval.
#   - If every attempt fails, logs a warning and returns. The pipeline
#     continues; stale module descriptions are treated as non-fatal.
#   - Does not modify any file outside fm_agent/.
# [SPEC]

# [INFO]
# build_llm_cli_command(model, prompt, cwd) -> list[str]
#   Pre-condition: model is a non-empty string identifying an LLM; prompt
#     is a non-empty string; cwd is a writable directory path.
#   Post-condition: Returns a list of strings forming a CLI command that,
#     when executed, invokes the configured agent backend with the given
#     model, prompt, and working directory.
# [SPLIT]
# run_opencode_traced(proj_dir, work_dir, command, stage, ...) -> CompletedProcess
#   Pre-condition: proj_dir is the project root path; work_dir is the
#     fm_agent workspace path; command is a non-empty list of CLI arguments;
#     stage is a pipeline stage identifier string.
#   Post-condition: Executes command as a subprocess, capturing stdout and
#     stderr. On successful completion (exit code 0), durably writes a
#     structured event record under fm_agent/trace/. On non-zero exit,
#     raises CalledProcessError with the exit code; the event record written
#     before the exception reflects the failure.
# [INFO]

def _update_module_description(proj_dir, work_dir, modified_modules):
    """Delegate refreshing module descriptions to the agent after deduplication.

    ``_ensure_source_files_in_phases`` can force-add source files to a module and
    ``_deduplicate_phases`` can strip duplicate source files from a module while
    leaving it in place. A module's ``description`` is prose written by the setup
    agent about a specific set of files, so once that set changes the description
    can be inaccurate. Rather than editing it mechanically, we hand the agent the
    exact list of modules whose file list changed and let it rewrite their
    descriptions against the freshly written phases.json.

    ``modified_modules`` is the list from ``_collect_changed_modules``; an empty
    list (no module's files changed) skips the agent call entirely.
    """
    if not modified_modules:
        return

    phases_path = os.path.join(work_dir, "phases.json")
    if not os.path.exists(phases_path):
        logging.info("No phases.json to update module descriptions in; skipping.")
        return

    prompt = _build_module_description_prompt(modified_modules, phases_path)
    if not prompt:
        logging.info(
            "No changed module still owns source files; skipping description update."
        )
        return
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
                stage="update_module_description",
                input_files=["fm_agent/phases.json"],
                output_files=["fm_agent/phases.json"],
                summary=f"Update module descriptions after phase dedup (attempt {attempt})",
                metadata={"attempt": attempt},
            )
            return
        except subprocess.CalledProcessError as e:
            logging.warning(
                "Module-description update attempt %d/%d failed: opencode exited %s",
                attempt, OPENCODE_MAX_RETRIES, e.returncode,
            )
            if attempt < OPENCODE_MAX_RETRIES:
                time.sleep(10)

    # Best effort: a stale description is not fatal to the pipeline, so warn and
    # let the run continue rather than aborting.
    logging.warning(
        "Module-description update did not complete after %d attempts; some module "
        "descriptions in phases.json may still reference deduplicated files.",
        OPENCODE_MAX_RETRIES,
    )
