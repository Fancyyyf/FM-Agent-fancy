# [SPEC]
# Unit: src/pipeline_setup-py/_run_generate_phases.py
#
# _run_generate_phases(proj_dir, work_dir, script_dir, is_incremental=False, resume=False, submodules=None) -> None
#
# Pre-condition:
#   - proj_dir, work_dir, and script_dir refer to existing directory paths
#   - is_incremental is a boolean; when truthy, a pre-existing phases.json under work_dir is updated in place rather than regenerated from scratch
#   - resume is a boolean
#   - submodules is None or a non-empty iterable of subdirectory name strings relative to proj_dir
#
# Post-condition:
#   - On normal return: phases.json exists under work_dir and conforms to the phases.json schema
#   - When resume is truthy and phases.json already satisfies the pipeline's completeness criteria, the function returns without producing or modifying any file
#   - When submodules is provided: phases.json covers all source files under the specified subdirectories of proj_dir; source files outside those subdirectories are neither added nor required to be present
#   - When is_incremental is truthy: a valid phases.json already present under work_dir may be accepted without modification if it covers all current source files, even when its modification timestamp has not changed
#   - If valid phases.json is not produced or confirmed after a configurable maximum number of retry attempts, the function prints a diagnostic message to stdout identifying the failed stage and the trace directory, then calls sys.exit(1)
#   - When a non-final attempt fails to produce valid phases.json, the function does not call sys.exit(1) — it waits a fixed interval before retrying
# [SPEC]

# [INFO]
# _phase_plan_complete(work_dir) -> bool
#   Pre-condition: work_dir is an existing directory path
#   Post-condition: Returns True when phases.json exists under work_dir and satisfies the pipeline's completeness criteria; returns False otherwise
# [SPLIT]
# _prepare_workflow_file(proj_dir, work_dir, script_dir, workflow_filename) -> None
#   Pre-condition: proj_dir, work_dir, script_dir are existing directory paths; workflow_filename is a string naming a workflow instruction file
#   Post-condition: The workflow instruction file is copied from script_dir into fm_agent/ under work_dir
# [SPLIT]
# build_llm_cli_command(model, prompt, cwd, files=None) -> CommandType
#   Pre-condition: model is a string identifying a configured LLM model; prompt is a non-empty string; cwd is an existing directory path; files is None or a list of file path strings
#   Post-condition: Returns a command suitable for execution that invokes the configured backend with the given prompt and file attachments in the specified working directory
# [SPLIT]
# run_opencode_traced(proj_dir, work_dir, command, stage, input_files, output_files, summary, metadata) -> CompletedProcess
#   Pre-condition: All arguments are well-formed; command is a list of strings constituting a valid CLI command
#   Post-condition: Executes the command as a subprocess within work_dir; on non-zero exit raises subprocess.CalledProcessError; records a trace event to fm_agent/trace/events.jsonl with the given stage, summary, and metadata; returns a CompletedProcess on zero exit
# [SPLIT]
# list_staged_domain_knowledge_relpaths(work_dir) -> list[str]
#   Pre-condition: work_dir is an existing directory path
#   Post-condition: Returns a sorted list of project-relative file paths for all user-provided domain knowledge files staged under spec_prompts/domain_context/user_knowledge/; returns an empty list when no files are staged
# [SPLIT]
# _phases_cover_current_sources(phases_json, proj_dir, submodules=None) -> bool
#   Pre-condition: phases_json is a path to an existing JSON file; proj_dir is an existing directory path; submodules is None or an iterable of subdirectory name strings
#   Post-condition: Returns True when phases_json is a readable, valid JSON file with at least one source file entry, every listed source file exists under proj_dir (and under a submodule if submodules is given), and every source file under the relevant directories is listed; returns False when any condition fails. Backslash separators in paths are treated as forward slashes.
# [SPLIT]
# _json_file_is_valid(phases_json) -> bool
#   Pre-condition: phases_json is a file path string
#   Post-condition: Returns True when the path refers to an existing regular file whose content is valid JSON; returns False otherwise
# [SPLIT]
# _phase_plan_schema_errors(phases_path) -> list[str]
#   Pre-condition: phases_path is a string.
#   Post-condition: Returns a list of human-readable error message strings; empty list indicates the file is valid JSON conforming to the required phases schema; non-empty list indicates an error such as missing file, invalid JSON, or schema violation.
# [INFO]

def _run_generate_phases(proj_dir, work_dir, script_dir, is_incremental=False,
                         resume=False, submodules=None):
    """Stage 1: generate phase.json — input target code, output phases.json."""
    phases_json = os.path.join(work_dir, "phases.json")
    prev_mtime = os.path.getmtime(phases_json) if os.path.exists(phases_json) else None

    phase_plan_errors = (
        _phase_plan_schema_errors(phases_json)
        if os.path.exists(phases_json)
        else []
    )
    _resume_skip = resume and _phase_plan_complete(work_dir)
    if _resume_skip:
        print("[Pipeline] Stage 1/6: RESUME — phases.json found, skipping phase plan generation.")

    _prepare_workflow_file(proj_dir, work_dir, script_dir, "workflow_generate_phases.md")

    fm_reminder = ("IMPORTANT: The fm_agent/ directory is NOT part of the project source code. "
                    "It is a workspace for storing your output files only. "
                    "Do NOT include fm_agent/ paths in phases.json. "
                    "Do NOT modify any existing project files.")
    incremental_reminder = ("IMPORTANT: An existing fm_agent/phases.json from a previous run is already "
                            "present. Do NOT regenerate it from scratch. Instead, inspect the current "
                            "state of the source code and UPDATE the existing fm_agent/phases.json so it "
                            "reflects the current version of the code: add modules and source files that "
                            "are new, remove entries whose files no longer exist, and adjust phases as "
                            "needed. Preserve entries that are still accurate.")
    submodule_reminder = ""
    if submodules:
        allowed = ", ".join(f"`{submodule}/`" for submodule in submodules)
        submodule_reminder = (
            "IMPORTANT: Only process source files under these project-relative "
            f"subdirectories: {allowed}. Do NOT include files outside these "
            "subdirectories in phases.json."
        )

    for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
        if _resume_skip:
            break
        if attempt == 1 and not resume:
            prompt = f"Follow the instructions in the attached file. {fm_reminder} {submodule_reminder}"
        else:
            prompt = ("A previous attempt was interrupted and may have already produced some of the "
                      "required output files. Follow the instructions in the attached file, but FIRST "
                      "check the current progress in fm_agent/ (e.g. phases.json). Keep any existing valid "
                      "output as-is and only generate the files that are missing or incomplete — do NOT "
                      f"regenerate or overwrite work that is already done. {fm_reminder} {submodule_reminder}")
        if is_incremental:
            prompt = f"{prompt} {incremental_reminder}"
        if phase_plan_errors:
            formatted_errors = "\n".join(
                f"- {error}" for error in phase_plan_errors
            )
            schema_repair_prompt = (
                "IMPORTANT: The existing fm_agent/phases.json is valid JSON or "
                "partially generated, but it does not match the required schema. "
                "Read the project source files and repair these problems:\n"
                f"{formatted_errors}\n"
                "Do not use an empty source_files array merely to satisfy the schema. "
                "Use an empty array only when the module genuinely owns no source files."
            )
            prompt = f"{prompt}\n\n{schema_repair_prompt}"
        prompt_file = os.path.join(proj_dir, "fm_agent", "workflow_generate_phases.md")
        command = build_llm_cli_command(
            model=OPENCODE_SETUP_MODEL,
            prompt=prompt,
            cwd=proj_dir,
            files=[prompt_file],
        )
        try:
            run_opencode_traced(
                proj_dir=proj_dir,
                work_dir=work_dir,
                command=command,
                stage="generate_phases_json",
                input_files=[
                    "fm_agent/workflow_generate_phases.md",
                    *list_staged_domain_knowledge_relpaths(work_dir),
                ],
                output_files=[
                    "fm_agent/phases.json",
                ],
                summary=f"OpenCode generate phases.json attempt {attempt}",
                metadata={"attempt": attempt},
            )
        except subprocess.CalledProcessError as e:
            logging.warning(f"Stage 1 attempt {attempt}: opencode exited with code {e.returncode}")

        phase_plan_errors = (
            _phase_plan_schema_errors(phases_json)
            if os.path.exists(phases_json)
            else ["phases.json is missing"]
        )

        phase_plan_ready = False
        if not phase_plan_errors:
            if submodules:
                phase_plan_ready = _phases_cover_current_sources(
                    phases_json, proj_dir, submodules
                )
            elif is_incremental:
                phase_plan_ready = (
                    os.path.getmtime(phases_json) != prev_mtime
                    or _phases_cover_current_sources(phases_json, proj_dir)
                )
            else:
                phase_plan_ready = True
        if phase_plan_ready:
            break

        failure = "update phases.json" if is_incremental else "produce phases.json"
        if phase_plan_errors:
            missing = (
                "phases.json schema validation failed: "
                + "; ".join(phase_plan_errors)
            )
        else:
            missing = (
                "phases.json was not updated"
                if is_incremental
                else "phases.json missing or invalid"
            )
        if attempt < OPENCODE_MAX_RETRIES:
            delay = 10
            print(
                f"[Pipeline] Stage 1 failed to {failure} (attempt {attempt}/{OPENCODE_MAX_RETRIES}). "
                f"Retrying in {delay}s..."
            )
            logging.warning(f"Stage 1 attempt {attempt} failed: {missing}. Retrying in {delay}s.")
            time.sleep(delay)
        else:
            print(
                f"[Pipeline] ERROR: Stage 1 failed after {OPENCODE_MAX_RETRIES} attempts. "
                f"{missing}. "
                f"Check {os.path.basename(proj_dir)}/fm_agent/trace/ for details."
            )
            sys.exit(1)
