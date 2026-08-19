import sys
import os
import tempfile
from pathlib import Path

# Ensure the repo root is importable (consistent with existing probes)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Save and sanitize environment to isolate the test
_saved_env = {k: os.environ.get(k) for k in (
    "FM_AGENT_CONFIG", "LLM_API_KEY", "LLM_API_BASE_URL",
    "FM_AGENT_MODEL_BACKEND", "LLM_MODEL", "LLM_EFFORT",
    "OPENCODE_MODEL_PROVIDER", "LLM_API_STYLE",
)}
for k in _saved_env:
    if k in os.environ:
        del os.environ[k]

# Set the CLI backend via env var so is_cli_backend_enabled() returns True
os.environ["FM_AGENT_MODEL_BACKEND"] = "codex-cli"

try:
    # Use the package entry point to import the function under test.
    # The spec claim: build_llm_cli_command must return a list of command-line
    # argument strings. The bug: when the CLI backend is enabled, the function
    # returns an AgentCommand object (not a list), violating the spec.
    from src.llm_client import build_llm_cli_command
    from src.cli_backend import AgentCommand

    result = build_llm_cli_command(
        model="test-model",
        prompt="test prompt",
        cwd="/tmp",
        files=["/tmp/a.txt", "/tmp/b.txt"],
    )

    # Spec requires a list[str]; the buggy code returns AgentCommand.
    actual_is_list = isinstance(result, list)
    expected_is_list = True
    passed = actual_is_list != expected_is_list  # True → bug reproduced

    if passed:
        print(
            f"CONFIRMED — actual: {type(result).__name__!r} "
            f"(not a list) | expected: list"
        )
    else:
        print(
            f"NOT CONFIRMED — actual matched expected (returned a list): "
            f"{result!r}"
        )
except Exception as exc:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {exc}")
finally:
    # Restore environment
    for k, v in _saved_env.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
