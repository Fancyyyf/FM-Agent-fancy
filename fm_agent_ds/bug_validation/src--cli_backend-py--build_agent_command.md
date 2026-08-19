# Bug Report: build_agent_command

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/cli_backend-py/build_agent_command.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns an AgentCommand dataclass. The argv field is a non-empty list of command-line argument strings that, when executed as a subprocess with cwd as the working directory, invokes the CLI backend identified by the backend field with the given model, prompt, and optional files. When files is non-empty, each file path appears exactly once as a file argument in the command list. When model is non-empty, the model name appears in the command list. When effort is non-empty, the effort value appears in the command list. The stdin field contains a string composed from the prompt text and optional file content, suitable as subprocess standard input. The backend field is either 'codex-cli' or 'claude-cli'. If the resolved backend is neither 'codex-cli' nor 'claude-cli', raises ValueError whose message identifies the unsupported backend name.

---

### Actual Behavior

One of the following holds: (1) A ValueError is raised if the resolved backend is not 'codex-cli' or 'claude-cli'. The resolved backend is determined as: let r1 = _normalize_backend(backend) if backend is not None else resolve_model_backend(); if r1 == 'auto' then resolved = resolve_model_backend() else resolved = r1. If resolved  {'codex-cli', 'claude-cli'}, raise ValueError with message containing the unsupported backend. (2) Otherwise, the function returns an AgentCommand object with attributes: backend = resolved; stdin = _compose_stdin(prompt, files or []); and argv is constructed as follows. Let cwd_abs = os.path.abspath(cwd). Let model_stripped = (model or '').strip(). (Since model is non-empty, model_stripped is non-empty.) Let effort_stripped = (effort if effort is not None else cli_effort()).strip(); effort_stripped is guaranteed non-empty. If resolved == 'codex-cli', argv = ['codex', 'exec', '--sandbox', 'danger-full-access', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-C', cwd_abs] + (['--model', model_stripped] if model_stripped else []) + (['-c', f'model_reasoning_effort=\"{effort_stripped}\"'] if effort_stripped else []) + ['-']. If resolved == 'claude-cli', argv = ['claude', '-p', '--output-format', 'text', '--no-session-persistence', '--dangerously-skip-permissions', '--permission-mode', 'bypassPermissions', '--add-dir', cwd_abs] + (['--model', model_stripped] if model_stripped else []) + (['--effort', effort_stripped] if effort_stripped else []).

---

## Code Evidence

Line 12-27, Line 28-44

---

## Trigger Condition

When files is non-empty, the specification requires each file path to appear exactly once as a file argument in the command list. However, the code never adds any file arguments to argv; neither the 'codex-cli' branch (lines 12-27) nor the 'claude-cli' branch (lines 28-44) include the given file paths. Therefore any input with a non-empty files list violates the specification.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| model | `"test-model"` |
| prompt | `"test prompt"` |
| cwd | `"/tmp/test-workdir"` |
| files | `["src/foo.py", "README.md"]` |
| backend | `"codex-cli"` |
| effort | `"high"` |

### Expected (spec-correct) Output

The `argv` list should contain `"src/foo.py"` and `"README.md"` as file arguments (each exactly once). The `stdin` field should contain the file-content prefix composed from the prompt and file paths.

### Actual (buggy) Output

The `argv` list is `['codex', 'exec', '--sandbox', 'danger-full-access', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-C', '/tmp/test-workdir', '--model', 'test-model', '-c', 'model_reasoning_effort="high"', '-']`. Neither `"src/foo.py"` nor `"README.md"` appears anywhere in `argv`. The file paths are only reflected in the `stdin` field (via `_compose_stdin`), not as command-line arguments.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.cli_backend import build_agent_command

result = build_agent_command(
    model="test-model",
    prompt="test prompt",
    cwd="/tmp/test-workdir",
    files=["src/foo.py", "README.md"],
    backend="codex-cli",
    effort="high",
)

# The argv list does not contain the file paths
print(result.argv)
# actual (buggy) output: ['codex', 'exec', ..., '-']
#                                 ^ no "src/foo.py" or "README.md"
# expected (correct) output: file paths should appear in argv

for f in ["src/foo.py", "README.md"]:
    assert f in result.argv, f"BUG: {f} not in argv"
```

---

## Probe Script

```python
"""Probe to confirm that build_agent_command() never adds file paths to argv.

Bug: When `files` is non-empty, the spec requires each file path to appear
exactly once as a file argument in argv. The code never adds file paths to
argv; they only influence stdin via _compose_stdin().
"""

import os
import sys
import tempfile

# Ensure the repo root is on sys.path so the public entry point resolves
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)

# The probe must work from a temp directory per FM-Agent self-validation guard
_work = tempfile.mkdtemp(prefix="bug_probe_")
_orig_cwd = os.getcwd()
try:
    os.chdir(_work)

    # Load the package through its public module path
    from src.cli_backend import build_agent_command, AgentCommand, resolve_model_backend

    # Determine a valid backend to test with
    backend = resolve_model_backend()
    if backend not in {"codex-cli", "claude-cli"}:
        # Try to force codex-cli
        backend = "codex-cli"

    test_files = ["src/foo.py", "README.md"]
    model_val = "test-model"
    prompt_val = "test prompt"
    cwd_val = "/tmp/test-workdir"

    result = build_agent_command(
        model=model_val,
        prompt=prompt_val,
        cwd=cwd_val,
        files=test_files,
        backend=backend,
        effort="high",
    )

    argv = result.argv

    # The spec says: "each file path appears exactly once as a file argument
    # in the command list." So we expect file paths to be present in argv.
    # The actual (buggy) behavior: no file paths in argv.

    files_found = any(f in argv for f in test_files)
    # Also search for any substring (e.g., a path might be reconstructed)
    partial_found = any(
        any(f_part in arg for f_part in f.split("/"))
        for f in test_files
        for arg in argv
    )

    # The bug is confirmed if no file path OR file name appears in argv
    bug_confirmed = not files_found and not partial_found

    if bug_confirmed:
        print(
            "CONFIRMED — bug reproduced: file paths absent from argv.\n"
            f"  argv:      {argv}\n"
            f"  files:     {test_files}\n"
            f"  backend:   {backend}\n"
            f"  stdin:     {result.stdin!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — file paths found in argv unexpectedly.\n"
            f"  argv:      {argv}\n"
            f"  files:     {test_files}\n"
            f"  backend:   {backend}"
        )

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

finally:
    os.chdir(_orig_cwd)
    # Clean up temp directory
    import shutil
    shutil.rmtree(_work, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — bug reproduced: file paths absent from argv.
  argv:      ['codex', 'exec', '--sandbox', 'danger-full-access', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-C', '/tmp/test-workdir', '--model', 'test-model', '-c', 'model_reasoning_effort="high"', '-']
  files:     ['src/foo.py', 'README.md']
  backend:   codex-cli
  stdin:     'Read these file(s) before acting:\n- src/foo.py\n- README.md\n\ntest prompt'
```
