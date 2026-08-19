def is_cli_backend_enabled():
    return resolve_model_backend() in {"codex-cli", "claude-cli"}
