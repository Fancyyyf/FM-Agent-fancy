# [SPEC]
# Unit: src/verification.py
#
# _validate_single_bug(result_json_rel, proj_dir, work_dir=None, resume=False)
#
# Pre-condition:
#   - result_json_rel is a non-empty string: the path (relative to proj_dir) of a
#     logic_verification_results/…json file whose verdict is "MISMATCH"
#   - proj_dir is an existing directory containing a readable md/bug_validator.md
#     and a writable fm_agent/ subtree
#   - work_dir is either None (defaults to proj_dir) or an existing directory
#     whose fm_agent/bug_validation/ tree is writable
#   - resume is a boolean; when True, a previous run may have left
#     fm_agent/bug_validation/<bug_id>.result.json under proj_dir
#
# Post-condition:
#   - Derives bug_id from result_json_rel deterministically: strips the prefix
#     "fm_agent/logic_verification_results/" (accepting both OS-dependent and "/"
#     separators), removes the file extension, then replaces every path separator
#     ("/" or os.sep) with "--"
#   - Reads md/bug_validator.md and assembles a per-bug prompt consisting of
#     a header identifying the target result file and the derived bug_id,
#     followed by an optional user-provided domain-knowledge section (when
#     staged knowledge files exist under work_dir), followed by the bug_validator
#     base content unmodified
#   - Atomically writes the assembled prompt to
#     fm_agent/bug_validation/bug_validator_{bug_id}.md under proj_dir
#     (writes to a ".tmp" sibling then os.replace, so no reader observes a
#     partial file)
#   - When resume is True and fm_agent/bug_validation/{bug_id}.result.json
#     already exists under proj_dir AND is valid JSON, returns immediately
#     without launching the bug-validation agent
#   - Otherwise, invokes the configured OpenCode bug-validation model (the model
#     identified by OPENCODE_BUG_VALIDATION_MODEL) with the prompt file as
#     context, recording trace events for the invocation
#   - Retries the invocation up to BUG_VALIDATION_MAX_RETRIES total attempts;
#     returns immediately once fm_agent/bug_validation/{bug_id}.result.json
#     exists under proj_dir
#   - Removes the generated prompt file (bug_validator_{bug_id}.md) from proj_dir
#     on exit regardless of success or failure (best-effort cleanup)
#   - Raises no uncaught exception to the caller; all subprocess failures are
#     logged and retried internally
# [SPEC]

# [INFO]
# function_id_from_result_path(result_json_rel) -> str
#   Pre-condition: result_json_rel is a string path relative to
#     fm_agent/logic_verification_results/
#   Post-condition: returns a function-identifier string derived from the
#     result path (the path with extension removed and path separators
#     replaced)
# [SPLIT]
# list_staged_domain_knowledge_relpaths(work_dir) -> list[str]
#   Pre-condition: work_dir is a valid directory path whose fm_agent/
#     subtree may contain staged domain-knowledge Markdown files
#   Post-condition: returns a list of relative paths (strings) to all staged
#     domain-knowledge Markdown files found under work_dir; returns an empty
#     list when none exist
# [SPLIT]
# format_domain_knowledge_bullets(user_knowledge_paths) -> str
#   Pre-condition: user_knowledge_paths is a non-empty list of file-path
#     strings, each pointing to a domain-knowledge Markdown file
#   Post-condition: returns a Markdown string consisting of a
#     "User-Provided Domain Knowledge" heading, a brief description, and a
#     bullet list of the given file paths
# [SPLIT]
# build_llm_cli_command(model, prompt, cwd, files) -> list[str]
#   Pre-condition: model is a non-empty model-name string,
#     prompt is a non-empty instruction string, cwd is a valid directory
#     path, files is a list of file-path strings to attach as context
#   Post-condition: returns a list of strings suitable for subprocess
#     invocation that runs the LLM CLI for the given model with the given
#     prompt, working directory, and context files
# [SPLIT]
# run_opencode_traced(proj_dir, work_dir, command, stage, function_ids,
#                     input_files, output_files, summary, metadata)
#   Pre-condition: proj_dir and work_dir are valid directory paths,
#     command is a non-empty list of strings, stage is a stage-identifier
#     string, and at least one of function_ids is non-empty
#   Post-condition: executes command as a subprocess, writes a trace event
#     to the fm_agent/trace/ directory, and raises CalledProcessError
#     if the subprocess exits with a non-zero return code
# [INFO]

def _validate_single_bug(result_json_rel, proj_dir, work_dir=None, resume=False):
    """Validate a single MISMATCH result by running opencode with a per-file prompt."""
    if work_dir is None:
        work_dir = proj_dir
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Derive bug id from result path relative to results dir
    # e.g. "fm_agent/logic_verification_results/mod/func.json" -> "mod--func"
    parts = result_json_rel
    prefix = os.path.join("fm_agent", "logic_verification_results") + os.sep
    if parts.startswith(prefix):
        parts = parts[len(prefix):]
    elif parts.startswith("fm_agent/logic_verification_results/"):
        parts = parts[len("fm_agent/logic_verification_results/"):]
    bug_id = os.path.splitext(parts)[0].replace(os.sep, "--").replace("/", "--")
    function_id = function_id_from_result_path(result_json_rel)

    # Read the base bug_validator.md
    base_md_path = os.path.join(script_dir, "md", "bug_validator.md")
    with open(base_md_path, "r") as f:
        base_content = f.read()

    user_knowledge_paths = list_staged_domain_knowledge_relpaths(work_dir)
    if user_knowledge_paths:
        user_knowledge_section = (
            "## User-Provided Domain Knowledge\n\n"
            "Read these Markdown files as additional context for intended behavior, "
            "terminology, data encodings, and invariants before validating the "
            "candidate bug:\n\n"
            f"{format_domain_knowledge_bullets(user_knowledge_paths)}\n\n---\n\n"
        )
    else:
        user_knowledge_section = ""

    # Generate a per-file prompt with target file and bug ID header
    prompt_content = (
        "# Bug Validator\n\n"
        f"**Target result file:** `{result_json_rel}`\n"
        f"**Bug ID:** `{bug_id}`\n\n---\n\n"
        + user_knowledge_section
        + base_content
    )

    os.makedirs(os.path.join(work_dir, "bug_validation"), exist_ok=True)

    prompt_filename = os.path.join(
        "fm_agent", "bug_validation", f"bug_validator_{bug_id}.md"
    )
    prompt_path = os.path.join(proj_dir, prompt_filename)

    tmp_path = prompt_path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(prompt_content)
    os.replace(tmp_path, prompt_path)

    prompt = "Follow the instructions in the attached file"
    command = build_llm_cli_command(
        model=OPENCODE_BUG_VALIDATION_MODEL,
        prompt=prompt,
        cwd=proj_dir,
        files=[prompt_path],
    )
    result_relpath = os.path.join("fm_agent", "bug_validation", f"{bug_id}.result.json")
    result_path = os.path.join(proj_dir, result_relpath)
    # Resume idempotency: if resuming and this bug was already validated, don't pay for it again.
    if resume and os.path.exists(result_path):
        try:
            with open(result_path) as _f:
                json.load(_f)
            logging.info(f"Bug validation already done, skipping: {bug_id}")
            return
        except (json.JSONDecodeError, OSError):
            pass  # corrupted result — re-validate
    try:
        max_attempts = config.BUG_VALIDATION_MAX_RETRIES
        for attempt in range(1, max_attempts + 1):
            run_failed = False
            try:
                run_opencode_traced(
                    proj_dir=proj_dir,
                    work_dir=work_dir,
                    command=command,
                    stage="bug_validation",
                    function_ids=[function_id],
                    input_files=[
                        prompt_filename,
                        result_json_rel,
                        *user_knowledge_paths,
                    ],
                    output_files=[
                        os.path.join("fm_agent", "bug_validation", f"{bug_id}.md"),
                        result_relpath,
                    ],
                    summary=f"OpenCode bug validation for {bug_id}",
                    metadata={"bug_id": bug_id, "result_json": result_json_rel},
                )
            except subprocess.CalledProcessError as exc:
                run_failed = True
                logging.warning(
                    "bug_validation run failed for %s on attempt %d/%d: %s",
                    bug_id,
                    attempt,
                    max_attempts,
                    exc,
                )

            if os.path.exists(result_path):
                return

            if attempt < max_attempts:
                logging.warning(
                    "bug_validation missing result artifact for %s after attempt %d/%d; retrying once",
                    bug_id,
                    attempt,
                    max_attempts,
                )
                continue

            logging.error(
                "bug_validation did not materialize %s after %d attempt(s)%s",
                result_relpath,
                max_attempts,
                " and a non-zero exit code" if run_failed else "",
            )
    finally:
        try:
            os.remove(prompt_path)
        except OSError:
            pass
