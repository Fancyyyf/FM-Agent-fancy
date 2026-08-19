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
