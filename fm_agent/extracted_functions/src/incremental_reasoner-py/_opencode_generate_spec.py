# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _opencode_generate_spec(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
#                          developer_intent, callee_names, source, caller_context)
#   -> dict | None
#
# Pre-condition:
#   - proj_dir is a path to an existing directory under version control
#   - work_dir is an absolute path to the fm_agent workspace directory,
#     which must exist and be writable
#   - idx is an integer used for naming intermediate output files uniquely
#   - fqn is a non-empty fully-qualified function name string
#     (e.g., "src::module::func")
#   - lang_key is a lowercase string identifying the programming language
#     (e.g., "python", "cpp", "rust")
#   - comment_prefix is the single-line comment marker for lang_key
#     (e.g., "#" for Python, "//" for C-family languages)
#   - developer_intent is a non-empty string describing the developer's
#     modification goal
#   - callee_names is a list of short callee name strings (the last
#     component of each callee FQN); it may be empty when the function
#     has no recorded callees
#   - source is a string containing the complete, non-empty source code
#     of the function
#   - caller_context is a list of (caller_fqn, spec_block, info_expectation)
#     tuples; each spec_block is the caller's full [SPEC] block text (may be
#     empty/absent), and each info_expectation is the text from the caller's
#     [INFO] entry describing what that caller needs from this function (may
#     be empty/absent); caller_context may be an empty list
#
# Post-condition:
#   - Writes a structured Markdown prompt to fm_agent/spec_generate_{idx}.md
#     whose content includes the function source, developer intent, callee
#     names, step-by-step instructions to read system_prompt.md and produce a
#     [SPEC] block (and, when callee_names is non-empty, an [INFO] block), and
#     the caller context sections (caller specs and caller expectations) when
#     caller_context is non-empty
#   - When staged domain knowledge files exist under work_dir, the prompt
#     includes an additional step instructing OpenCode to read and use those
#     files as context
#   - Delegates execution to _opencode_select_json, which writes the prompt
#     to disk, invokes OpenCode as a subprocess, and blocks until the
#     subprocess terminates
#   - When the subprocess terminates successfully and writes valid JSON to
#     fm_agent/spec_generate_{idx}.json, returns a dict with exactly these keys:
#       "spec_updated": bool — True if and only if a [SPEC] block was produced
#       "new_spec": string — the generated [SPEC] block text including its
#         opening and closing markers, or "" when no block was produced
#       "info_updated": bool — True if and only if an [INFO] block was produced
#       "new_info": string — the generated [INFO] block text, or ""
#       "updated_callees": list of strings — callee names recorded in the
#         generated [INFO] block, or an empty list
#   - Returns None when the subprocess exits with a non-zero status or when
#     the file at the result path cannot be parsed as a valid JSON object
#     containing the expected keys
#   - Does not modify the source code of any function; all writes go to
#     fm_agent/ workspace files
# [SPEC]

# [INFO]
# list_staged_domain_knowledge_relpaths(work_dir) -> list[str]
#   Pre-condition: work_dir is an absolute path to an existing, readable
#     subdirectory under proj_dir
#   Post-condition: Returns a list of relative path strings (using "/"
#     separators) for domain knowledge Markdown files that have been staged
#     under the workspace; returns an empty list when no files are staged
# [SPLIT]
# format_domain_knowledge_bullets(paths) -> str
#   Pre-condition: paths is a list of relative file path strings (may be empty)
#   Post-condition: Returns a single string where each path is rendered as
#     a bullet item suitable for embedding in a Markdown prompt; returns an
#     empty string when paths is empty
# [SPLIT]
# _opencode_select_json(proj_dir, work_dir, prompt_relpath, prompt_content,
#                       result_relpath, stage, input_files)
#   -> dict | None
#   Pre-condition: all arguments are non-None; prompt_content is a non-empty
#     string; prompt_relpath and result_relpath are relative paths within
#     proj_dir whose parent directories exist; input_files is a list of
#     relative file paths to make available to the subprocess
#   Post-condition: Writes prompt_content to the file at prompt_relpath,
#     invokes OpenCode as a subprocess with proj_dir as the working directory
#     and with input_files declared as context files, blocks until the
#     subprocess terminates, reads the file at result_relpath, and returns
#     the parsed JSON dict from that file; returns None when the subprocess
#     exits with a non-zero status or when result_relpath does not contain
#     valid JSON after the subprocess terminates
# [INFO]

def _opencode_generate_spec(proj_dir, work_dir, idx, fqn, lang_key, comment_prefix,
                            developer_intent, callee_names, source, caller_context):
    """
    Ask opencode to generate a brand-new [SPEC] (and, when the function has callees, [INFO])
    block from scratch for a function that has no existing specification — e.g. a function
    freshly added by the modification.

    Mirrors the full run's spec generation (run_pipeline Stage 6) but for a single function:
    opencode reads the project's spec format rules (fm_agent/spec_prompts/system_prompt.md),
    is given the same caller context the full run provides (each caller's [SPEC] block and what
    that caller's [INFO] block expects from this function, in caller_context as returned by
    _collect_caller_context), and produces the block(s) directly. Returns the parsed decision
    in the SAME shape as _opencode_check_spec_update so the caller can splice and propagate it
    identically.

    Returns the parsed result dict — keys: "spec_updated" (bool, true when a [SPEC] block was
    produced), "new_spec" (str), "info_updated" (bool), "new_info" (str), "updated_callees"
    (list[str]) — or None when opencode produced nothing usable.
    """
    result_relpath = os.path.join("fm_agent", f"spec_generate_{idx}.json")
    prompt_relpath = os.path.join("fm_agent", f"spec_generate_{idx}.md")

    # Caller context (callers' own specs + what each caller's [INFO] expects from this
    # function), mirroring run_pipeline's "EARLIER-LAYER CALLER SPECS" / "CALLEE EXPECTATIONS
    # FROM CALLERS" sections so the generated spec satisfies what callers depend on.
    caller_specs = [
        (cfqn, spec) for cfqn, spec, _ in caller_context if spec
    ]
    caller_expectations = [
        (cfqn, exp) for cfqn, _, exp in caller_context if exp
    ]
    caller_section = ""
    if caller_specs:
        caller_section += "## Specs of this function's callers\n\n"
        for cfqn, spec in caller_specs:
            caller_section += f"### {cfqn}\n\n{spec.strip()}\n\n"
    if caller_expectations:
        caller_section += (
            "## What callers expect from this function (from their [INFO] blocks)\n\n"
            "Your generated [SPEC] must be consistent with these expectations.\n\n"
        )
        for cfqn, exp in caller_expectations:
            caller_section += f"### According to {cfqn}\n\n{exp.strip()}\n\n"

    callee_hint = ", ".join(sorted(callee_names)) if callee_names else "(none)"
    user_knowledge_paths = list_staged_domain_knowledge_relpaths(work_dir)
    if user_knowledge_paths:
        user_knowledge_step = (
            "2. Read these user-provided domain knowledge Markdown files and use "
            "them as additional context:\n"
            f"{format_domain_knowledge_bullets(user_knowledge_paths)}\n"
        )
        step_offset = 1
    else:
        user_knowledge_step = ""
        step_offset = 0
    info_step_number = 3 + step_offset
    if callee_names:
        info_step = (
            f"{info_step_number}. Because this function has callees, also produce an [INFO] block recording the "
            "expected behavioral spec of each callee it depends on (the `[INFO]` ... `[INFO]` "
            f"block only, markers included, every line prefixed with `{comment_prefix}`), and "
            "list the names of the callees you recorded.\n"
        )
    else:
        info_step = f"{info_step_number}. This function has no callees, so produce no [INFO] block.\n"

    prompt_content = (
        "# Generate Function Specification\n\n"
        "A modification has been applied to a codebase to achieve the developer intent below, "
        "adding a function that has no behavioral specification yet. Generate its "
        "specification from scratch.\n\n"
        f"- Function fully-qualified name: `{fqn}` (language: `{lang_key}`).\n"
        f"- Comment prefix for this language: `{comment_prefix}`.\n"
        f"- Known callees of this function: {callee_hint}.\n\n"
        "## Developer intent\n\n"
        f"{developer_intent}\n\n"
        "## Function source\n\n"
        f"```{lang_key}\n{source.strip()}\n```\n\n"
        f"{caller_section}"
        "## Steps\n\n"
        "1. Read `fm_agent/spec_prompts/system_prompt.md` for the exact [SPEC]/[INFO] format "
        "rules used by this project.\n"
        f"{user_knowledge_step}"
        f"{2 + step_offset}. Produce the COMPLETE [SPEC] block describing this function's behavior — the "
        "`[SPEC]` ... `[SPEC]` block only, markers included, every line prefixed with "
        f"`{comment_prefix}`, and NO source code.\n"
        f"{info_step}"
        f"{4 + step_offset}. Write your answer to `{result_relpath}` as a JSON object with keys:\n"
        '   - "spec_updated": boolean — true when you produced a [SPEC] block.\n'
        '   - "new_spec": string — the full [SPEC] block.\n'
        '   - "info_updated": boolean — true when you produced an [INFO] block.\n'
        '   - "new_info": string — the full [INFO] block, or "" if none.\n'
        '   - "updated_callees": array of callee name strings recorded in [INFO], or [].\n'
        "   Write ONLY that JSON file; do not modify any other project files.\n"
    )

    return _opencode_select_json(
        proj_dir,
        work_dir,
        prompt_relpath,
        prompt_content,
        result_relpath,
        stage="generate_function_spec",
        input_files=[
            prompt_relpath,
            "fm_agent/spec_prompts/system_prompt.md",
            *user_knowledge_paths,
        ],
    )
