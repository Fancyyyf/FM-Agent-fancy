"""Probe script: confirm resolve_model_backend returns values outside the allowed set."""
import sys
import os

# Ensure the repo root is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

ALLOWED_BACKENDS = {"codex-cli", "claude-cli", "opencode"}

try:
    from config import settings
    from src.cli_backend import resolve_model_backend

    # Inject an unrecognized backend value — per the spec, the function
    # must return one of the allowed backends, but the code returns the
    # normalized value unchanged for any unknown backend.
    settings.llm.backend = "unknown_backend"

    actual = resolve_model_backend()
    bug_reproduced = actual not in ALLOWED_BACKENDS
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_reproduced:
    print(f"CONFIRMED — actual: {actual!r} | allowed set: {ALLOWED_BACKENDS!r}")
else:
    print(f"NOT CONFIRMED — actual matched allowed set: {actual!r}")
