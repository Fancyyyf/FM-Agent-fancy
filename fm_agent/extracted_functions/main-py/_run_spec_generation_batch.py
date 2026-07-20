# [SPEC]
# Unit: main.py
#
# _run_spec_generation_batch(proj_dir, work_dir, attempt, phase_num, layer_idx, batch_rel_dir, batch_info) -> int
#
# Pre-condition:
#   - proj_dir is a string path to the project root directory
#   - work_dir is a string path to the fm_agent workspace directory
#   - attempt is a positive integer: 1 for initial run, >1 for retry
#   - phase_num and layer_idx identify the phase and layer of the batch
#   - batch_rel_dir is the relative directory path containing the batch prompt file
#   - batch_info is a dict containing at minimum the key "file" whose value is the batch prompt filename; it may also contain a "functions" key whose value is a list of extracted function file paths relative to the project root
#
# Post-condition:
#   - Invokes an agent process to generate behavioral specifications for the functions listed in the batch prompt file
#   - On attempt == 1: the agent is instructed to process all functions listed in the batch prompt
#   - On attempt > 1: the agent is instructed to check each function file and only generate specs for those that lack a [SPEC] block
#   - The agent invocation is recorded in the trace (inputs, outputs, timing, outcome)
#   - Input files tracked for tracing include: the batch workflow instructions, the batch prompt file, the spec format rules, and any staged domain knowledge files
#   - Returns the integer exit code of the agent process: 0 indicates success, nonzero indicates failure
#   - If the agent process raises CalledProcessError, returns its exit code rather than propagating the exception
# [SPEC]

# [INFO]
# function_id_from_extracted_path(func_rel) -> str
#   Pre-condition: func_rel is a relative path to an extracted function file, using "/" separators
#   Post-condition: Returns the fully-qualified function name (FQN) derived by replacing the file extension separator with "::" and joining all path components with "::"
# [SPLIT]
# build_llm_cli_command(model, prompt, cwd, files) -> list[str]
#   Pre-condition: model is a model identifier string; prompt is the instruction text; cwd is the working directory; files is an optional list of file paths to include as context
#   Post-condition: Returns a CLI argument list that, when executed, invokes the configured LLM backend with the given model, prompt, working directory, and context files
# [SPLIT]
# run_opencode_traced(proj_dir, work_dir, command, stage, function_ids, input_files, output_files, summary, metadata) -> CompletedProcess
#   Pre-condition: command is a CLI argument list; stage identifies the pipeline stage; function_ids, input_files, output_files are optional lists; summary and metadata are optional
#   Post-condition: Executes command as a subprocess with timeout handling; writes a structured trace event recording start/end time, exit status, metadata, and file references; returns a CompletedProcess with the exit code
# [SPLIT]
# list_staged_domain_knowledge_relpaths(work_dir) -> list[str]
#   Pre-condition: work_dir is a string path to the fm_agent workspace directory
#   Post-condition: Returns a sorted list of project-relative paths (using "/" separators) of all domain knowledge files staged under spec_prompts/domain_context/user_knowledge/
# [INFO]

def _run_spec_generation_batch(
    proj_dir,
    work_dir,
    attempt,
    phase_num,
    layer_idx,
    batch_rel_dir,
    batch_info,
):
    # Run one batch end-to-end so the executor can refill slots as soon as a
    # batch finishes, instead of waiting for a whole chunk barrier.
    batch_file = batch_info["file"]
    batch_prompt_rel = os.path.join(batch_rel_dir, batch_file)
    function_files = batch_info.get("functions", [])
    function_ids = [
        function_id_from_extracted_path(func_rel)
        for func_rel in function_files
    ]
    fm_reminder = ("IMPORTANT: fm_agent/ is your output workspace, not project source. "
                    "Do NOT modify any existing project files.")
    if attempt == 1:
        prompt = (
            f"Process the batch prompt file at {batch_prompt_rel}. "
            f"Read it and fm_agent/spec_prompts/system_prompt.md, "
            f"generate behavioral specs for each function listed, "
            f"and write the complete specced files directly. {fm_reminder}"
        )
    else:
        prompt = (
            f"Continue processing the batch prompt file at {batch_prompt_rel}. "
            f"Some functions may already have specs from a previous attempt. "
            f"Check each function file — only generate specs for those "
            f"that don't have [SPEC] blocks yet. "
            f"Read fm_agent/spec_prompts/system_prompt.md for the format rules. {fm_reminder}"
        )
    prompt_file = os.path.join(proj_dir, "fm_agent", "workflow_spec_step4_batch.md")
    command = build_llm_cli_command(
        model=OPENCODE_SPEC_MODEL,
        prompt=prompt,
        cwd=proj_dir,
        files=[prompt_file],
    )
    try:
        result = run_opencode_traced(
            proj_dir=proj_dir,
            work_dir=work_dir,
            command=command,
            stage="spec_generation",
            function_ids=function_ids,
            input_files=[
                "fm_agent/workflow_spec_step4_batch.md",
                batch_prompt_rel,
                "fm_agent/spec_prompts/system_prompt.md",
                *list_staged_domain_knowledge_relpaths(work_dir),
            ],
            output_files=function_files,
            summary=f"OpenCode spec generation for {batch_file}",
            metadata={
                "attempt": attempt,
                "phase": phase_num,
                "layer": layer_idx,
                "batch_file": batch_file,
            },
        )
        return result.returncode
    except subprocess.CalledProcessError as exc:
        return exc.returncode
