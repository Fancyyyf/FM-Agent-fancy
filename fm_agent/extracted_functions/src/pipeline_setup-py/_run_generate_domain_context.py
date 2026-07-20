# [SPEC]
# Unit: src/pipeline_setup-py/_run_generate_domain_context.py
#
# _run_generate_domain_context(proj_dir, work_dir, script_dir, resume=False) -> None
#
# Pre-condition:
#   - proj_dir, work_dir, and script_dir refer to existing directory paths
#   - phases.json exists under work_dir
#   - resume is a boolean
#
# Post-condition:
#   - On normal return: the directory spec_prompts/domain_context/ within work_dir contains engine_overview.txt and exactly one file matching the pattern phase_NN_types.txt for each phase defined in phases.json
#   - When resume is truthy and the domain context files under spec_prompts/domain_context/ already satisfy the pipeline's completeness criteria, the function returns without producing or modifying any files
#   - If complete domain context is not produced after a configurable maximum number of retry attempts, the function prints a diagnostic message to stdout identifying the failed stage and the trace directory, then calls sys.exit(1)
#   - When a non-final attempt fails to produce complete domain context, the function does not call sys.exit(1) — it waits a fixed interval before retrying
#   - Staged domain knowledge files under spec_prompts/domain_context/user_knowledge/ are supplied as inputs to the generation process
# [SPEC]

# [INFO]
# _domain_context_complete(work_dir) -> bool
#   Pre-condition: work_dir is an existing directory path
#   Post-condition: Returns True when the domain context files under spec_prompts/domain_context/ satisfy the pipeline's completeness criteria; returns False otherwise
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
# [INFO]

def _run_generate_domain_context(proj_dir, work_dir, script_dir, resume=False):
    """Stage 2: generate domain context — input phases.json, output domain context
    files for each phase.
    """
    _resume_skip = resume and _domain_context_complete(work_dir)
    if _resume_skip:
        print("[Pipeline] Stage 2/6: RESUME — domain context files found, skipping domain context generation.")

    _prepare_workflow_file(proj_dir, work_dir, script_dir, "workflow_generate_domain_context.md")

    fm_reminder = ("IMPORTANT: The fm_agent/ directory is NOT part of the project source code. "
                    "It is a workspace for storing your output files only. "
                    "Do NOT modify any existing project files.")

    for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
        if _resume_skip:
            break
        if attempt == 1 and not resume:
            prompt = (
                "Read fm_agent/phases.json first. "
                "Then follow the instructions in the attached file. "
                + fm_reminder
            )
        else:
            prompt = ("A previous domain-context generation attempt was interrupted and may have already "
                      "produced some of the required output files. Read fm_agent/phases.json first. "
                      "Then follow the instructions in the attached file, but FIRST "
                      "check the current progress in fm_agent/spec_prompts/domain_context/. "
                      "Keep any existing valid output as-is and only generate the files that are missing or "
                      f"incomplete — do NOT regenerate or overwrite work that is already done. {fm_reminder}")
        prompt_file = os.path.join(proj_dir, "fm_agent", "workflow_generate_domain_context.md")
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
                stage="generate_domain_context",
                input_files=[
                    "fm_agent/workflow_generate_domain_context.md",
                    "fm_agent/phases.json",
                    *list_staged_domain_knowledge_relpaths(work_dir),
                ],
                output_files=[
                    "fm_agent/spec_prompts/domain_context/engine_overview.txt",
                ],
                summary=f"OpenCode generate domain context attempt {attempt}",
                metadata={"attempt": attempt},
            )
        except subprocess.CalledProcessError as e:
            logging.warning(f"Stage 2 attempt {attempt}: opencode exited with code {e.returncode}")

        if _domain_context_complete(work_dir):
            break

        if attempt < OPENCODE_MAX_RETRIES:
            delay = 10
            print(
                f"[Pipeline] Stage 2 failed to produce domain context "
                f"(attempt {attempt}/{OPENCODE_MAX_RETRIES}). "
                f"Retrying in {delay}s..."
            )
            logging.warning(f"Stage 2 attempt {attempt} failed: domain context outputs missing. Retrying in {delay}s.")
            time.sleep(delay)
        else:
            print(
                f"[Pipeline] ERROR: Stage 2 failed after {OPENCODE_MAX_RETRIES} attempts. "
                f"Domain context outputs missing. "
                f"Check {os.path.basename(proj_dir)}/fm_agent/trace/ for details."
            )
            sys.exit(1)
