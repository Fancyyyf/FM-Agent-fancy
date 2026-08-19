def _prompt_backend() -> str:
    print()
    print("Model backend:")
    print("  1. OpenCode")
    print("  2. Auto-detect local Codex or Claude CLI")
    print("  3. Codex CLI")
    print("  4. Claude CLI")
    selected = _prompt("Select", "1")
    backends = {
        "1": "opencode",
        "2": "auto",
        "3": "codex-cli",
        "4": "claude-cli",
    }
    try:
        return backends[selected]
    except KeyError as exc:
        raise ConfigWizardError("Backend selection must be 1, 2, 3, or 4.") from exc
