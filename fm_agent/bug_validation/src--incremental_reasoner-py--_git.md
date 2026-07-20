# Bug Report: _git

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Executes git with -C proj_dir subcommand args using subprocess
  - Returns the stdout output of the git command as a single string
  - Raises subprocess.CalledProcessError when the git command exits with
    a nonzero exit code

---

### Actual Behavior

If the `git` executable is found, the command `git -C proj_dir *args` is executed with `check=True`, `capture_output=True`, and `text=True`. Under the pre-condition that `args[0]` is a valid git subcommand and the rest are acceptable arguments, and `proj_dir` is a directory containing a git repository, execution yields exactly one of: (1) the command exits with code 0, and the returned value is the captured stdout as a string; (2) the command exits with a non-zero code, and a `subprocess.CalledProcessError` is raised, with `returncode`, `cmd`, `output`, and `stderr` attributes reflecting the failure. If the `git` executable does not exist, a `FileNotFoundError` is raised. No other side effects occur beyond any performed by the git command itself on the repository.

---

## Code Evidence

Line 2:         return subprocess.run(

---

## Trigger Condition

The specification requires that the code 'executes git'. In the case where git is not found, the code raises FileNotFoundError, failing to execute git and raising an exception not covered by the specification (which only allows CalledProcessError for nonzero exit codes).

---

## How to trigger the bug

The `_git` nested function inside `_collect_changed_functions()` in `src/incremental_reasoner.py` calls `subprocess.run(["git", ...], check=True, ...)`. When the `git` executable is not present on the system PATH, Python's `subprocess.run` raises `FileNotFoundError` — an exception not mentioned in the specification, which only covers `CalledProcessError` for nonzero exit codes.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/tmp/dummy_proj_dir` |
| old_commit_id | `dummy_commit_1234abcd` |
| PATH (environment) | `/tmp/no-git-here` (no git available) |

### Expected (spec-correct) Output

`CalledProcessError` raised with returncode, cmd, output, and stderr attributes reflecting the failure.

### Actual (buggy) Output

`FileNotFoundError` raised — the git executable could not be found.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import sys
sys.path.insert(0, '.')
os.environ['PATH'] = '/tmp/no-git-here'

from src.incremental_reasoner import _collect_changed_functions
_collect_changed_functions('/tmp/dummy_proj_dir', 'dummy_commit_1234abcd')
# actual (buggy) output: FileNotFoundError: [Errno 2] No such file or directory: 'git'
# expected (correct) output: CalledProcessError
```

---

## Probe Script

```python
"""Probe for _git: FileNotFoundError not covered by spec."""
import os
import sys
import subprocess

# Add repo root to Python path (probe is at fm_agent/bug_validation/, 3 levels deep)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Save original PATH and remove git from it to trigger FileNotFoundError
original_path = os.environ.get('PATH', '')
os.environ['PATH'] = '/tmp/no-git-here'

try:
    from src.incremental_reasoner import _collect_changed_functions

    # Call the function that contains the nested _git helper.
    # With git absent from PATH, the first subprocess.run(["git", ...]) inside _git
    # will raise FileNotFoundError — which the spec does not allow
    # (spec only permits CalledProcessError for nonzero exit codes).
    _collect_changed_functions('/tmp/dummy_proj_dir', 'dummy_commit_1234abcd')

    # If we reach here, no exception was raised → bug NOT reproduced
    print('NOT CONFIRMED — _collect_changed_functions completed without raising FileNotFoundError')

except FileNotFoundError:
    # The spec only allows CalledProcessError for nonzero exit codes.
    # FileNotFoundError is NOT in the spec → bug CONFIRMED.
    print('CONFIRMED — FileNotFoundError raised when git not found on PATH (spec only allows CalledProcessError)')

except subprocess.CalledProcessError as e:
    print(f'NOT CONFIRMED — CalledProcessError raised (as spec requires): {e}')

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')

finally:
    os.environ['PATH'] = original_path
```

### Probe Output

```
CONFIRMED — FileNotFoundError raised when git not found on PATH (spec only allows CalledProcessError)
```
