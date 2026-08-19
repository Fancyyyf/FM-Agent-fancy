"""Probe for bug: _elp_argv unconditionally appends "server", creating a duplicate
when the ELP_COMMAND already includes the "server" subcommand.

Bug ID: src--languages--erlang-py--_elp_argv

Expected (spec): the final element is "server", and the preceding elements form
a platform-appropriate ELP invocation without a duplicate "server".

Actual (bug): the function blindly appends "server" to the parsed argv, so a
command like "elp server" produces ['elp', 'server', 'server'].
"""

import os
import sys
from pathlib import Path

# Ensure the repo root and src/ are importable (same pattern as other probes).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC = _REPO_ROOT / "src"
for p in (str(_REPO_ROOT), str(_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Save and sanitize environment to isolate the test.
_saved_env = {k: os.environ.get(k) for k in (
    "ELP_COMMAND", "ELP_TIMEOUT_SECONDS", "FM_AGENT_CONFIG",
    "LLM_API_KEY", "LLM_API_BASE_URL", "FM_AGENT_MODEL_BACKEND",
    "LLM_MODEL", "LLM_EFFORT", "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
    "MAX_SPC_ITER", "GRANULARITY", "MAX_WORKERS", "OPENCODE_MAX_RETRIES",
    "BUG_VALIDATION_MAX_RETRIES", "OPENCODE_TIMEOUT_SECONDS",
    "FM_AGENT_DOMAIN_KNOWLEDGE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

try:
    import config
    from languages.erlang import _elp_argv

    # --- Step 1: Default command (no server) — should work correctly ---
    config.settings.erlang.command = "elp"
    result_default = _elp_argv()
    assert result_default[-1] == "server", f"Expected last element to be 'server', got: {result_default}"
    assert result_default.count("server") == 1, (
        f"Default command should produce exactly one 'server', got: {result_default}"
    )

    # --- Step 2: Command already contains "server" subcommand ---
    # This is the trigger condition described in the bug report.
    # If a user configures ELP_COMMAND="elp server", the parsed argv already
    # contains "server", and appending another creates a duplicate.
    config.settings.erlang.command = "elp server"
    result_duplicate = _elp_argv()

    # The spec says the preceding elements should be a valid ELP invocation
    # without duplicate tokens. '["elp", "server", "server"]' is not valid.
    has_duplicate = result_duplicate.count("server") > 1

    if has_duplicate:
        expected_spec = ["elp", "server"]  # what a correct invocation would look like
        print(
            f"CONFIRMED — _elp_argv() returns a list with duplicate 'server': "
            f"actual: {result_duplicate!r} | "
            f"expected (no duplicate): {expected_spec!r}"
        )
    else:
        # If no duplicate, the function happened to produce a correct result
        # (e.g. shlex.split produced something unexpected).
        print(
            f"NOT CONFIRMED — no duplicate 'server' in result: {result_duplicate!r}"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")

finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
