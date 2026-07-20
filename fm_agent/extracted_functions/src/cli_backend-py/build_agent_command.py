# [SPEC]
# Unit: fm_agent/extracted_functions/src/cli_backend-py/build_agent_command.py
#
# build_agent_command(model, prompt, cwd, files=None, backend=None, effort=None) -> AgentCommand
#
# Pre-condition:
#   - model is a non-empty string identifying an LLM model
#   - prompt is a non-empty string
#   - cwd is a path to an existing directory
#   - files is either None or a list of file path strings (may be empty)
#   - backend is either None or a string identifying a desired CLI backend
#   - effort is either None or a string
#
# Post-condition:
#   - The effective backend is determined by normalizing the provided backend
#     argument (resolving alias names) when non-None, or by reading the
#     configured default model backend when backend is None; the sentinel
#     value "auto" resolves to a concrete backend
#   - Raises ValueError with a message identifying the unsupported backend
#     when the effective backend is not a supported CLI backend
#   - Returns an AgentCommand whose argv is a non-empty list of argument
#     strings that, when executed via subprocess with cwd resolved to an
#     absolute path as the working directory, invokes the effective backend
#     to process prompt using model
#   - When files is a non-empty list, the prompt text and the contents of
#     each listed file are combined into the AgentCommand's stdin field;
#     each file path in files is attached as context to the backend
#     invocation
#   - When files is None or an empty list, the AgentCommand's stdin field is
#     None
#   - When effort is provided and non-empty, or when effort is None and a
#     configured default effort is set and non-empty, the reasoning effort
#     level is included in the backend invocation arguments
#   - The AgentCommand's backend field records the canonical name of the
#     effective backend
# [SPEC]

# [INFO]
# _normalize_backend(backend_str) -> str
#   Pre-condition: backend_str is a string (may be empty)
#   Post-condition: Returns the canonical backend name; recognized aliases
#     are normalized to their canonical forms (e.g., "codex" → "codex-cli",
#     "claude" → "claude-cli")
# [SPLIT]
# resolve_model_backend() -> str
#   Pre-condition: None (reads environment or configuration)
#   Post-condition: Returns the canonical backend name of the configured
#     model backend; "auto" resolves to a concrete backend
# [SPLIT]
# _compose_stdin(prompt, files) -> Optional[str]
#   Pre-condition: prompt is a non-empty string; files is a list of file
#     path strings (may be empty)
#   Post-condition: Returns a string that combines the prompt text with the
#     contents of the listed files, formatted for use as stdin to the
#     backend subprocess; returns None when files is empty
# [SPLIT]
# cli_effort() -> str
#   Pre-condition: None (reads environment or configuration)
#   Post-condition: Returns the configured reasoning effort level as a
#     string, or an empty string when no effort level is configured
# [SPLIT]
# AgentCommand(argv, stdin, backend) -> AgentCommand
#   Pre-condition: argv is a list of argument strings; stdin is a string
#     or None; backend is a canonical backend name string
#   Post-condition: Returns an AgentCommand dataclass whose argv field is
#     argv, whose stdin field is stdin, and whose backend field is backend
# [INFO]

def build_agent_command(model, prompt, cwd, files=None, backend=None, effort=None):
    resolved = _normalize_backend(backend) if backend else resolve_model_backend()
    if resolved == "auto":
        resolved = resolve_model_backend()
    if resolved not in {"codex-cli", "claude-cli"}:
        raise ValueError(f"unsupported CLI backend: {resolved}")

    cwd = os.path.abspath(cwd)
    stdin = _compose_stdin(prompt, files or [])
    model = (model or "").strip()
    effort = (effort if effort is not None else cli_effort()).strip()

    if resolved == "codex-cli":
        argv = [
            "codex",
            "exec",
            "--sandbox",
            "danger-full-access",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            cwd,
        ]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["-c", f'model_reasoning_effort="{effort}"']
        argv.append("-")
        return AgentCommand(argv=argv, stdin=stdin, backend=resolved)

    argv = [
        "claude",
        "-p",
        "--output-format",
        "text",
        "--no-session-persistence",
        "--dangerously-skip-permissions",
        "--permission-mode",
        "bypassPermissions",
        "--add-dir",
        cwd,
    ]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    return AgentCommand(argv=argv, stdin=stdin, backend=resolved)
