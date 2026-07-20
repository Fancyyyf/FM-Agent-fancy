# [SPEC]
# Unit: src/cli_backend-py/is_cli_backend_enabled.py
#
# is_cli_backend_enabled() -> bool
#
# Pre-condition:
#   - The backend configuration has been loaded and its module-level state is initialized
#
# Post-condition:
#   - Returns True when the configured model backend resolves to a direct CLI backend (Codex CLI or Claude CLI)
#   - Returns False when the configured model backend resolves to the OpenCode backend
# [SPEC]

# [INFO]
# resolve_model_backend() -> str
#   Pre-condition: the backend configuration has been loaded and module-level state is initialized
#   Post-condition: returns the canonical backend identifier ("opencode", "codex-cli", or "claude-cli"),
#     with any configured alias resolved to its canonical form
# [INFO]

def is_cli_backend_enabled():
    return resolve_model_backend() in {"codex-cli", "claude-cli"}
