# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_opencode_select_json.py
#
# _opencode_select_json(proj_dir, work_dir, prompt_relpath, prompt_content,
#                       result_relpath, stage, input_files) -> dict | list | None
#
# Pre-condition:
#   - proj_dir is a valid writable directory
#   - work_dir is a directory path
#   - prompt_relpath identifies a path under proj_dir whose parent directory exists
#   - prompt_content is a non-empty string
#   - result_relpath identifies a path under proj_dir whose parent directory exists
#   - stage is a non-empty string identifier
#   - input_files is a list (possibly empty) of file paths
#
# Post-condition:
#   - The full prompt_content is present at proj_dir/prompt_relpath when the LLM agent is invoked
#   - Any pre-existing file at proj_dir/result_relpath is removed before the first LLM invocation
#   - An LLM agent is invoked to read the prompt and may write a JSON artifact to result_relpath
#   - The invocation is retried up to a configurable maximum number of times when result_relpath is not produced
#   - A fixed delay elapses between consecutive retry attempts
#   - Each invocation attempt is traced as an observable event
#   - Returns the parsed JSON value (dict or list) when result_relpath is produced and its content is valid JSON
#   - Returns None when result_relpath is never produced within the retry limit, or when the file content is not valid JSON or cannot be read
#   - A non-zero exit code from the LLM agent does not determine the return value — only the presence and parseability of result_relpath does
# [SPEC]

# [INFO]
# build_llm_cli_command(model, prompt, cwd, files) -> str
#   Pre-condition: model is a non-empty string; prompt is a non-empty string; cwd is a valid directory path; files is a list of absolute file paths
#   Post-condition: Returns a CLI command string that, when executed, invokes the LLM with the given model, prompt, working directory, and file context
# [SPLIT]
# run_opencode_traced(proj_dir, work_dir, command, stage, input_files, output_files, summary, metadata) -> None
#   Pre-condition: proj_dir and work_dir are valid directory paths; command is a non-empty string; stage is a non-empty string; input_files and output_files are lists of file paths; summary is a non-empty string; metadata is a dict
#   Post-condition: Executes command with tracing recorded for the given stage; raises subprocess.CalledProcessError when the command exits with a non-zero code
# [INFO]

def _opencode_select_json(proj_dir, work_dir, prompt_relpath, prompt_content,
                          result_relpath, stage, input_files):
    """
    Run opencode to produce a JSON artifact and return the parsed JSON.

    Writes prompt_content to proj_dir/prompt_relpath, removes any stale artifact at
    proj_dir/result_relpath, then runs `opencode run --file <prompt> -- ...` (with the same
    retry / result-artifact check used by the setup stage) until the agent writes the
    result file. Returns the parsed JSON value, or None if opencode never produced the
    artifact or it could not be parsed. Shared by the module- and file-selection steps of
    collect_relevent_function_scope.
    """
    prompt_path = os.path.join(proj_dir, prompt_relpath)
    result_path = os.path.join(proj_dir, result_relpath)
    if os.path.exists(result_path):
        os.remove(result_path)

    tmp_path = prompt_path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(prompt_content)
    os.replace(tmp_path, prompt_path)

    prompt = "Follow the instructions in the attached file."
    command = build_llm_cli_command(
        model=OPENCODE_SETUP_MODEL,
        prompt=prompt,
        cwd=proj_dir,
        files=[prompt_path],
    )

    produced = False
    for attempt in range(1, OPENCODE_MAX_RETRIES + 1):
        try:
            run_opencode_traced(
                proj_dir=proj_dir,
                work_dir=work_dir,
                command=command,
                stage=stage,
                input_files=input_files,
                output_files=[result_relpath],
                summary=f"OpenCode {stage} attempt {attempt}",
                metadata={"attempt": attempt},
            )
        except subprocess.CalledProcessError as exc:
            logging.warning(
                "%s: opencode exited with code %s (attempt %d/%d)",
                stage, exc.returncode, attempt, OPENCODE_MAX_RETRIES,
            )

        if os.path.exists(result_path):
            produced = True
            break

        if attempt < OPENCODE_MAX_RETRIES:
            logging.warning(
                "%s: %s not produced (attempt %d/%d); retrying in 10s",
                stage, result_relpath, attempt, OPENCODE_MAX_RETRIES,
            )
            time.sleep(10)

    if not produced:
        logging.error(
            "%s: %s not produced after %d attempts", stage, result_relpath, OPENCODE_MAX_RETRIES
        )
        return None

    try:
        with open(result_path, "r") as f:
            return json.load(f)
    except (ValueError, OSError) as exc:
        logging.error("%s: could not read %s: %s", stage, result_relpath, exc)
        return None
