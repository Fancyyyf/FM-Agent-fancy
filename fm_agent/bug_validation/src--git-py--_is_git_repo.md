# Bug Report: _is_git_repo

**Source file:** `src/git.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True if and only if proj_dir is a git repository with a resolvable
    HEAD commit (the directory is recognized by git as a repository and contains
    at least one commit).
  - Returns False if proj_dir is not a git repository or is a git repository
    with no commits.
  - The function does not raise exceptions to its callers; all outcomes are
    expressed via the boolean return value.

---

### Actual Behavior

After the execution of the block, the function _is_git_repo either returns a boolean or raises an exception. (1) If it returns True, then proj_dir is a valid git repository containing at least one commit (the command 'git -C proj_dir rev-parse --verify HEAD' exits with status 0). (2) If it returns False, then the command raised subprocess.CalledProcessError (nonzero exit status), meaning proj_dir is either not a git repository or has no commits. (3) If an exception is raised, it is not subprocess.CalledProcessError; it could be any other exception from subprocess.run (e.g., FileNotFoundError, PermissionError). The function has no side effects: proj_dir and the global state remain unchanged. Formally: (return = True)  (git_exit_code = 0  valid_git_repo_with_commits(proj_dir)); (return = False)  (git_exit_code  0  valid_git_repo_with_commits(proj_dir)); (exception E)  E  CalledProcessError; proj_dir_out = proj_dir_in  unchanged_global_state.

---

## Code Evidence

Line 9: except subprocess.CalledProcessError:

---

## Trigger Condition

The specification requires that the function never raises exceptions to its callers; all outcomes must be expressed via the boolean return value. However, if the 'git' executable is not present or not in PATH, subprocess.run raises FileNotFoundError, which is not caught by the narrow except clause. This causes the function to propagate an exception instead of returning False, violating the specification.

---

## How to trigger the bug

When the `git` executable is not available in the system PATH, calling `_is_git_repo()` raises `FileNotFoundError` instead of returning `False`, violating the specification's requirement that all outcomes are expressed via boolean return values.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `.` (current directory) |
| PATH environment | `/tmp/nonexistent_dir_xyz` (no `git` on PATH) |

### Expected (spec-correct) Output

`False` (the function should never raise; non-git conditions → False)

### Actual (buggy) Output

`FileNotFoundError: [Errno 2] No such file or directory: 'git'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from src.git import _is_git_repo

saved_path = os.environ["PATH"]
os.environ["PATH"] = "/tmp/nonexistent_dir_xyz"
_is_git_repo(".")  # Raises FileNotFoundError instead of returning False
os.environ["PATH"] = saved_path
# actual (buggy) output: FileNotFoundError: [Errno 2] No such file or directory: 'git'
# expected (correct) output: False
```

---

## Probe Script

```python
"""Probe script for bug _is_git_repo: FileNotFoundError not caught."""
import sys
import os

# Add repo root to sys.path so that "import src" resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.git import _is_git_repo

# Temporarily clear PATH so 'git' cannot be found, triggering FileNotFoundError
saved_path = os.environ.get("PATH", "")
os.environ["PATH"] = "/tmp/nonexistent_dir_xyz"

try:
    actual = _is_git_repo(".")
    # If we reach here, no exception was raised. The spec says it should return
    # False when the directory is not a valid git repo or has no commits.
    # With git missing from PATH, it can't tell, but it shouldn't crash.
    expected = False  # spec: never raises, returns bool
    passed = actual is not False  # True if it returned True incorrectly
    if passed:
        print(f"UNEXPECTED — returned {actual!r} when git was missing from PATH")
    else:
        print(f"NOT CONFIRMED — function returned False as expected (no exception)")
except FileNotFoundError as e:
    # Bug confirmed: exception raised instead of returning False
    print(f"CONFIRMED — FileNotFoundError raised instead of returning False: {e}")
except Exception as e:
    print(f"CONFIRMED — unexpected exception raised instead of returning False: {type(e).__name__}: {e}")
finally:
    os.environ["PATH"] = saved_path
```

### Probe Output

```
CONFIRMED — FileNotFoundError raised instead of returning False: [Errno 2] No such file or directory: 'git'
```
