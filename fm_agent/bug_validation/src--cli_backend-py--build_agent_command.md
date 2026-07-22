# Bug Report: build_agent_command

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/cli_backend-py/build_agent_command.py`
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

Let B, M, P, D, F, E denote the formal parameters backend, model, prompt, cwd, files, effort respectively. Define:

1. N = if B is not None then _normalize_backend(B) else resolve_model_backend()
2. R = if N == "auto" then resolve_model_backend() else N

If R  {"codex-cli", "claude-cli"}, a ValueError is raised.

Otherwise, let:
  C = os.path.abspath(D)
  S = _compose_stdin(P, F if F is not None else [])
      (by spec, S is None when F is None or empty, else a string.)
  M' = M.strip()                        (may be empty even if M was nonempty)
  E' = (E if E is not None else cli_effort()).strip()

if R = "codex-cli":
    argv = ["codex","exec","--sandbox","danger-full-access",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check","-C", C]
         + (["--model", M'] if M' != "" else [])
         + (["-c", f'model_reasoning_effort="{E'}"'] if E' != "" else [])
         + ["-"]
    return a value r with r.argv = argv, r.stdin = S, r.backend = "codex-cli"

if R = "claude-cli":
    argv = ["claude","-p","--output-format","text",
            "--no-session-persistence","--dangerously-skip-permissions",
            "--permission-mode","bypassPermissions","--add-dir", C]
         + (["--model", M'] if M' != "" else [])
         + (["--effort", E'] if E' != "" else [])
    return a value r with r.argv = argv, r.stdin = S, r.backend = "claude-cli"

No other side effects occur.

---

## Code Evidence

Line 12: construction of argv for codex-cli does not attach files as context; Line 28: construction of argv for claude-cli does not attach files as context; the requirement to attach each file path as context to the backend invocation is not implemented anywhere in the function.

---

## Trigger Condition

The specification requires that when files is a non-empty list, each file path is attached as context to the backend invocation (i.e., appears in argv as arguments). The code only combines file contents into stdin but never adds the file paths to argv. With the given input (files=['a.txt','b.txt']), the returned AgentCommand.argv lacks any file-related flags like '--file a.txt', violating the specification.

---

## How to trigger the bug

Call `build_agent_command` with a non-empty `files` list. The returned `AgentCommand.argv` will contain no reference to any of the file paths — neither as separate arguments nor as part of a flag like `--file`. The spec requires that each file path be attached as context to the backend invocation (i.e., appear in `argv`).

### Inputs

| Parameter | Value |
|-----------|-------|
| model | `"test-model"` |
| prompt | `"test prompt"` |
| cwd | `"/tmp"` |
| files | `["a.txt", "b.txt"]` |
| backend | `"codex-cli"` (also tested: `"claude-cli"`) |
| effort | (omitted, defaults to configured via `cli_effort()`) |

### Expected (spec-correct) Output

`AgentCommand.argv` contains arguments referencing each file path in `files` (e.g., `"--file a.txt --file b.txt"` or equivalent context-attaching flags for the respective backend).

### Actual (buggy) Output

`AgentCommand.argv` contains zero references to the file paths `a.txt` or `b.txt`. For `codex-cli`, the argv is:
```
["codex", "exec", "--sandbox", "danger-full-access", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check", "-C", "/tmp", "--model", "test-model", "-"]
```

For `claude-cli`, the argv is:
```
["claude", "-p", "--output-format", "text", "--no-session-persistence", "--dangerously-skip-permissions", "--permission-mode", "bypassPermissions", "--add-dir", "/tmp", "--model", "test-model"]
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')

from src.cli_backend import build_agent_command

# Test with codex-cli
cmd = build_agent_command(
    model="test-model",
    prompt="test prompt",
    cwd="/tmp",
    files=["a.txt", "b.txt"],
    backend="codex-cli",
)
print("argv:", cmd.argv)
# actual (buggy) output: argv has no 'a.txt' or 'b.txt'
# expected (correct) output: argv includes file paths as context arguments

print("Does argv contain file paths?", any(f in str(cmd.argv) for f in ["a.txt", "b.txt"]))
# actual (buggy) output: False
# expected (correct) output: True
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on sys.path so 'config' and 'src' packages are importable.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.cli_backend import build_agent_command
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

test_files = ["a.txt", "b.txt"]
backends_to_test = ["codex-cli", "claude-cli"]

all_confirmed = True
details = []

for backend in backends_to_test:
    try:
        cmd = build_agent_command(
            model="test-model",
            prompt="test prompt",
            cwd="/tmp",
            files=test_files,
            backend=backend,
        )
    except Exception as e:
        print(f'ERROR building command for {backend}: {e}')
        sys.exit(1)

    argv_flat = " ".join(cmd.argv)
    file_in_argv = any(f in argv_flat for f in test_files)

    if file_in_argv:
        details.append(f'{backend}: file paths FOUND in argv → spec satisfied → NOT CONFIRMED')
        all_confirmed = False
    else:
        details.append(f'{backend}: file paths MISSING from argv → spec violated → CONFIRMED')

# Print verdict
if all_confirmed:
    print('CONFIRMED — file paths missing from argv for all backends:', ' | '.join(details))
else:
    print('NOT CONFIRMED — file paths found in argv for at least one backend:', ' | '.join(details))
```

### Probe Output

```
CONFIRMED — file paths missing from argv for all backends: codex-cli: file paths MISSING from argv → spec violated → CONFIRMED | claude-cli: file paths MISSING from argv → spec violated → CONFIRMED
```
