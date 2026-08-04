def resolve_model_backend():
    backend = _normalize_backend(settings.llm.backend)
    if backend != "auto":
        return backend

    host_hint = (os.environ.get("FM_AGENT_HOST") or os.environ.get("FM_AGENT_CLIENT") or "").lower()
    if "claude" in host_hint:
        return "claude-cli"
    if "codex" in host_hint:
        return "codex-cli"

    claude_markers = ("CLAUDE_PLUGIN_ROOT", "CLAUDE_CODE_ENTRYPOINT")
    if any(os.environ.get(name) for name in claude_markers):
        return "claude-cli"

    codex_markers = ("CODEX_HOME", "CODEX_SANDBOX", "CODEX_EXECUTION_MODE")
    if any(os.environ.get(name) for name in codex_markers):
        return "codex-cli"

    return "codex-cli"
