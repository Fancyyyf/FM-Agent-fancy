# [SPEC]
# Unit: src/cli_backend.py
#
# resolve_model_backend() -> str
#
# Pre-condition:
#   - settings.llm.backend contains a string value (the configured model backend)
#   - The process environment may or may not contain variables named
#     FM_AGENT_HOST or FM_AGENT_CLIENT, whose values are any strings
#   - The process environment may or may not contain any of the markers
#     CLAUDE_PLUGIN_ROOT, CLAUDE_CODE_ENTRYPOINT, CODEX_HOME,
#     CODEX_SANDBOX, or CODEX_EXECUTION_MODE
#
# Post-condition:
#   - Returns a canonical backend identifier string: one of "opencode",
#     "codex-cli", or "claude-cli"
#   - The returned backend is first determined by normalizing
#     settings.llm.backend via _normalize_backend; if the result is not
#     "auto", that result is returned immediately
#   - When the normalized value of settings.llm.backend is "auto", the
#     backend is determined by inspecting environment markers in a fixed
#     priority order:
#       1. FM_AGENT_HOST or FM_AGENT_CLIENT (whichever is set) is checked
#          case-insensitively for "claude" or "codex" substrings
#       2. The presence of any Claude-specific environment variable
#          (CLAUDE_PLUGIN_ROOT, CLAUDE_CODE_ENTRYPOINT)
#       3. The presence of any Codex-specific environment variable
#          (CODEX_HOME, CODEX_SANDBOX, CODEX_EXECUTION_MODE)
#   - The first matching marker in this priority order determines the
#     returned backend: "claude-cli" for Claude markers, "codex-cli" for
#     Codex markers
#   - When no marker matches, returns "codex-cli" (the default fallback)
#   - The same input (settings.llm.backend value and environment state)
#     always produces the same output (pure function with respect to its
#     inputs at call time)
# [SPEC]

# [INFO]
# _normalize_backend(name) -> str
#   Pre-condition: name is a string identifier that may be a canonical
#     backend name ("opencode", "codex-cli", "claude-cli") or an alias
#     ("codex", "claude", "open-code") or any other string
#   Post-condition: returns the canonical backend name corresponding to
#     name when name is a recognized alias, or name itself unchanged when
#     name is not a recognized alias
# [INFO]

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
