# Bug Report: _path_exists_in_commit

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True when rel_path identifies an object present at old_commit_id in the repository at proj_dir. Returns False when no such object exists at that revision or when the git command fails for any other reason. Never raises an exception.

---

### Actual Behavior

The function returns a boolean. It returns True if and only if the git command `git -C proj_dir cat-file -e old_commit_id:rel_path` exits with a return code of 0, which indicates that the object (file or directory) at the given relative path exists in the specified commit of the repository located at `proj_dir`. If the command fails for any reason (including the path not existing or external errors), the return code is non-zero and the function returns False. No exceptions are raised. 

Formally: Let cmd = ['git', '-C', proj_dir, 'cat-file', '-e', f"{old_commit_id}:{rel_path}"]. Then _path_exists_in_commit(rel_path) == (subprocess.run(cmd, check=False, capture_output=True, text=True).returncode == 0).

---

## Code Evidence

Line 3: return subprocess.run(
Line 4:     ["git", "-C", proj_dir, "cat-file", "-e", f"{old_commit_id}:{rel_path}"],
Line 5:     check=False,
Line 6:     capture_output=True,
Line 7:     text=True,
Line 8: ).returncode == 0

---

## Trigger Condition

The code runs a git command via subprocess.run without handling non-zero exit or OSError. If git is missing, subprocess.run raises FileNotFoundError, so the function raises an exception instead of returning False as required by the specification's 'Returns False when ... the git command fails for any other reason. Never raises an exception.'

---

## How to trigger the bug

When `git` is not installed on the system (or not on PATH), calling `_collect_changed_functions()` triggers `_path_exists_in_commit()`, which calls `subprocess.run(["git", ...])` without a try/except. Python's `subprocess.run` raises `FileNotFoundError` when the executable is not found, and this exception propagates uncaught, violating the spec's guarantee: "Never raises an exception."

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Any directory (e.g. `/tmp/fake_probe_repo`) |
| `old_commit_id` | Any commit hash (e.g. `abc1234`) |
| `git installation` | Git missing from system PATH |

### Expected (spec-correct) Output

`False` — the function should return `False` when git fails for any reason, including `git` not being found.

### Actual (buggy) Output

`FileNotFoundError: [Errno 2] No such file or directory: 'git'` — an uncaught exception propagates from `subprocess.run`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from unittest import mock
import subprocess

import src.incremental_reasoner

def mock_run(cmd, **kwargs):
    if "cat-file" in " ".join(cmd):
        raise FileNotFoundError("No such file or directory: 'git'")
    if "diff --name-only" in " ".join(cmd):
        return subprocess.CompletedProcess(cmd, 0, stdout="src/__init__.py\n", stderr="")
    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

with mock.patch("subprocess.run", side_effect=mock_run):
    src.incremental_reasoner._collect_changed_functions("/tmp/fake", "abc1234")
# raises FileNotFoundError — actual (buggy) output: FileNotFoundError
# expected (correct) output: False (returned, no exception)
```

---

## Probe Script

```python
"""Probe for _path_exists_in_commit: FileNotFoundError when git is missing.

Bug ID: src--incremental_reasoner-py--_collect_changed_functions::_path_exists_in_commit
Spec claim: Returns False when the git command fails for any reason. Never raises an exception.
Bug: subprocess.run with check=False raises FileNotFoundError when git is not on PATH,
     instead of returning False.
"""
import sys
import subprocess
from unittest import mock

# Ensure the project root is on sys.path so `import src` resolves
sys.path.insert(0, ".")


def mock_run(cmd, *, check=False, capture_output=False, text=False, **_kwargs):
    """Selective mock: succeed for all git commands EXCEPT cat-file (simulates git missing)."""
    cmd_str = " ".join(cmd)

    if "cat-file" in cmd_str:
        raise FileNotFoundError(f"[Errno 2] No such file or directory: 'git'")

    if "diff --name-only" in cmd_str:
        # Return a file so _collect_changed_functions enters the per-file loop
        return subprocess.CompletedProcess(
            cmd, 0, stdout="src/__init__.py\n", stderr=""
        )

    if "ls-files" in cmd_str:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    if "show" in cmd_str:
        # _funcs_from_commit -> git show <commit>:<path>
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    if "worktree" in cmd_str:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def main():
    try:
        import src.incremental_reasoner

        with mock.patch("subprocess.run", side_effect=mock_run):
            try:
                # _collect_changed_functions:
                # 1. _git("diff") → returns "src/__init__.py" → enters loop
                # 2. _path_exists_in_commit("src/__init__.py") → cat-file → FileNotFoundError
                result = src.incremental_reasoner._collect_changed_functions(
                    "/tmp/fake_probe_repo", "abc1234"
                )
                print("NOT CONFIRMED — FileNotFoundError was handled (exception caught)")
            except FileNotFoundError as e:
                print(f"CONFIRMED — FileNotFoundError propagated: {e}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — FileNotFoundError propagated: [Errno 2] No such file or directory: 'git'
```
