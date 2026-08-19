# Bug Report: build_llm_cli_command

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/llm_client-py/build_llm_cli_command.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of command-line argument strings that, when executed as a subprocess with cwd as the working directory, invokes the configured LLM backend with the given model, prompt, and files. Each file path in files (when files is not None and non-empty) is present exactly once in the returned command list as a file argument. The prompt string is the final positional argument in the returned command list. The command list uses the backend determined by the global runtime configuration: when the backend is codex-cli or claude-cli, the command list reflects that backend's argument conventions; otherwise the command list uses the opencode run argument conventions.

---

### Actual Behavior

If is_cli_backend_enabled() is True, the function returns an AgentCommand object (from build_agent_command(model, prompt, cwd, files)) whose argv field, when executed as a subprocess in directory cwd, invokes the configured CLI backend (codex-cli or claude-cli) with the given model, prompt, and each file path from files (if files is not None) appearing exactly once as a file argument. If is_cli_backend_enabled() is False, the function returns a list of strings: ['opencode', 'run', '--model', f'{OPENCODE_MODEL_PROVIDER}/{model}'] concatenated with ['--file', f] for each f in (files if files is not None else []), then concatenated with ['--', prompt]. No side effects occur; cwd is not modified.

---

## Code Evidence

Line 8: return build_agent_command(model=model, prompt=prompt, cwd=cwd, files=files)

---

## Trigger Condition

The specification explicitly requires the function to return a list of command-line argument strings. When the CLI backend is enabled, the code returns an AgentCommand object (which is not a list), directly violating the specified return type.

---

## How to trigger the bug

When the CLI backend is enabled (e.g., configured via `FM_AGENT_MODEL_BACKEND=codex-cli`), calling `build_llm_cli_command` returns an `AgentCommand` object instead of a `list[str]` as required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| model | `"test-model"` |
| prompt | `"test prompt"` |
| cwd | `"/tmp"` |
| files | `["/tmp/a.txt", "/tmp/b.txt"]` |

### Expected (spec-correct) Output

A `list` of command-line argument strings.

### Actual (buggy) Output

An `AgentCommand` object (not a list).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
os.environ["FM_AGENT_MODEL_BACKEND"] = "codex-cli"

from src.llm_client import build_llm_cli_command

result = build_llm_cli_command(
    model="test-model",
    prompt="test prompt",
    cwd="/tmp",
    files=["/tmp/a.txt", "/tmp/b.txt"],
)

# actual (buggy) output: AgentCommand(argv=[...], stdin=..., backend='codex-cli')
# expected (correct) output: list of argument strings (e.g., ['codex', 'exec', ...])
print(type(result).__name__)  # prints "AgentCommand" (not "list")
print(isinstance(result, list))  # prints False
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — actual: 'AgentCommand' (not a list) | expected: list
```
