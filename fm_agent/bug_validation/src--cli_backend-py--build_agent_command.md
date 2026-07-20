# Bug Report: build_agent_command

**Source file:** `src/cli_backend.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- The effective backend is determined by normalizing the provided backend
    argument (resolving alias names) when non-None, or by reading the
    configured default model backend when backend is None; the sentinel
    value "auto" resolves to a concrete backend
  - Raises ValueError with a message identifying the unsupported backend
    when the effective backend is not a supported CLI backend
  - Returns an AgentCommand whose argv is a non-empty list of argument
    strings that, when executed via subprocess with cwd resolved to an
    absolute path as the working directory, invokes the effective backend
    to process prompt using model
  - When files is a non-empty list, the prompt text and the contents of
    each listed file are combined into the AgentCommand's stdin field;
    each file path in files is attached as context to the backend
    invocation
  - When files is None or an empty list, the AgentCommand's stdin field is
    None
  - When effort is provided and non-empty, or when effort is None and a
    configured default effort is set and non-empty, the reasoning effort
    level is included in the backend invocation arguments
  - The AgentCommand's backend field records the canonical name of the
    effective backend

---

### Actual Behavior

If the resolved backend is not in {'codex-cli', 'claude-cli'}, a ValueError is raised with the message 'unsupported CLI backend: {resolved}'. Otherwise, the function returns an AgentCommand object. The resolved backend is computed as: Let raw = _normalize_backend(backend) if backend is not None and backend != '' else resolve_model_backend(); then resolved = resolve_model_backend() if raw == 'auto' else raw. Let cwd_abs = os.path.abspath(cwd), std = _compose_stdin(prompt, files if files is not None else []), m = (model or '').strip(), e = (effort if effort is not None else cli_effort()).strip(). Then:
- If resolved == 'codex-cli', the returned AgentCommand has backend='codex-cli', stdin=std, and argv = ['codex', 'exec', '--sandbox', 'danger-full-access', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-C', cwd_abs] + (['--model', m] if m != '' else []) + (['-c', 'model_reasoning_effort="' + e + '"'] if e != '' else []) + ['-'].
- If resolved == 'claude-cli', the returned AgentCommand has backend='claude-cli', stdin=std, and argv = ['claude', '-p', '--output-format', 'text', '--no-session-persistence', '--dangerously-skip-permissions', '--permission-mode', 'bypassPermissions', '--add-dir', cwd_abs] + (['--model', m] if m != '' else []) + (['--effort', e] if e != '' else []).

Formally:
 model, prompt, cwd, files, backend, effort. Pre-condition holds 
  let r = (backend  None  backend  "") ? _normalize_backend(backend) : resolve_model_backend() in
  let r' = (r = "auto" ? resolve_model_backend() : r) in
  (r'  {"codex-cli", "claude-cli"}  result = ValueError("unsupported CLI backend: " + r'))

---

## Code Evidence

Line 8: files are only used to compute stdin via _compose_stdin; no further statements add file path arguments to argv. Line 12-21 (codex-cli argv building) and Line 28-39 (claude-cli argv building) do not include file path arguments.

---

## Trigger Condition

The specification requires that when 'files' is a non-empty list, each file path is attached as context to the backend invocation (e.g., passed as arguments). The code only combines prompt and file contents into stdin but does not add any file path arguments to the argv list, so the backend receives no direct context of the file paths.

---

## How to trigger the bug

Call `build_agent_command` with a non-empty `files` list. The returned `AgentCommand.argv` will not contain any file path arguments — only the `stdin` field includes file content hints. The specification requires file paths to be attached as context arguments to the backend CLI invocation.

### Inputs

| Parameter | Value |
|-----------|-------|
| model | `"test-model"` |
| prompt | `"test prompt"` |
| cwd | `<repo root>` |
| files | `["test_file.txt"]` |
| backend | `"codex-cli"` |
| effort | (not set) |

### Expected (spec-correct) Output

`AgentCommand.argv` should contain `"test_file.txt"` (or an equivalent flag + path) so the backend receives the file path as invocation context.

### Actual (buggy) Output

`AgentCommand.argv` does NOT contain `"test_file.txt"` — only stdin carries file information.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.cli_backend import build_agent_command

cmd = build_agent_command(
    model="test-model",
    prompt="test prompt",
    cwd=".",
    files=["test_file.txt"],
    backend="codex-cli",
)
print(cmd.argv)
# actual (buggy) output: ['codex', 'exec', '--sandbox', 'danger-full-access', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-C', '<cwd>', '--model', 'test-model', '-']
# expected (correct) output: argv should contain 'test_file.txt'
```

---

## Probe Script

```python
import sys
import os

# Add repo root to path so the "src" package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from src.cli_backend import build_agent_command
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

actual = None
expected = None
passed = None

try:
    cwd = os.path.abspath(os.getcwd())
    files = ["test_file.txt"]

    actual = build_agent_command(
        model="test-model",
        prompt="test prompt",
        cwd=cwd,
        files=files,
        backend="codex-cli",
    )

    # Spec says: "each file path in files is attached as context to the
    # backend invocation." That means file paths SHOULD appear in argv.
    # Bug claim: the code only composes stdin, never adds file paths to argv.
    file_path_in_argv = any("test_file.txt" in arg for arg in actual.argv)
    expected_contains_files = True
    passed = not file_path_in_argv  # bug confirmed when files NOT in argv

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — file path 'test_file.txt' NOT found in argv: {actual.argv}")
else:
    print(f"NOT CONFIRMED — file path found in argv: {actual.argv}")
```

### Probe Output

```
CONFIRMED — file path 'test_file.txt' NOT found in argv: ['codex', 'exec', '--sandbox', 'danger-full-access', '--dangerously-bypass-approvals-and-sandbox', '--skip-git-repo-check', '-C', '/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot', '--model', 'test-model', '-']
```
