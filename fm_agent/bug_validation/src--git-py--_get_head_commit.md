# Bug Report: _get_head_commit

**Source file:** `src/git.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If proj_dir refers to a git repository whose HEAD commit is resolvable, returns
    the full SHA-1 hash of HEAD as a non-empty stripped string.
  - If proj_dir is not a git repository or does not have a resolvable HEAD commit,
    returns None.
  - The function does not raise exceptions to its callers; all failures are
    expressed via a None return.

---

### Actual Behavior

Natural language: The function `_get_head_commit` takes a string `proj_dir` and, if it returns normally, returns either a string representing the latest Git commit ID (the stripped stdout of `git rev-parse HEAD` executed in `proj_dir`) or `None`. When `proj_dir` is a valid Git repository, the function returns that commit string and no additional side effect occurs. When `proj_dir` is not a Git repository (i.e., `git rev-parse` fails with a `CalledProcessError`), the function logs an info message containing `proj_dir` and returns `None`. If an unexpected exception (e.g., missing `git`) is raised, the function propagates the exception and does not return. The passed `proj_dir` remains unchanged. 

Formal logic: 
Let R be the return value of the function upon normal termination. 
Let GIT_SUCCESS(proj_dir) be true iff the subprocess `['git', '-C', proj_dir, 'rev-parse', 'HEAD']` completes with return code 0 and produces a non-trivial output (string). 
Then: 
- (NormalTermination  GIT_SUCCESS(proj_dir))  (isinstance(R, str)  R = strip(subprocess.stdout)  no logging side effect). 
- (NormalTermination  GIT_SUCCESS(proj_dir)  caught CalledProcessError)  (R is None   info log record: 'INFO: _get_head_commit: {proj_dir} is not a git repo.'). 
- If any other exception (not CalledProcessError) occurs during subprocess.run, the function terminates abnormally; no post-condition about return value applies.

---

## Code Evidence

Line 3: try:
Line 8: except subprocess.CalledProcessError:

---

## Trigger Condition

Condition B specifies that all failures must be expressed via a None return and no exceptions should be raised to callers. However, the code only catches subprocess.CalledProcessError. If the 'git' command is not found (FileNotFoundError) or any other unexpected exception occurs, the function propagates the exception, violating the specification.

---

## How to trigger the bug

The bug occurs when the `git` binary is unavailable on the system PATH. The function calls `subprocess.run(["git", ...])`, and when `git` cannot be found, Python raises `FileNotFoundError`. Since `_get_head_commit` only catches `subprocess.CalledProcessError`, the `FileNotFoundError` propagates uncaught to the caller — violating the spec requirement that all failures must be expressed via a `None` return.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Current working directory (a valid git repository path) |

### Expected (spec-correct) Output

`None` — the spec requires the function to return `None` for all failure cases.

### Actual (buggy) Output

`FileNotFoundError: [Errno 2] No such file or directory: 'git'` — the exception propagates uncaught.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
from src.git import _get_head_commit

# Temporarily clear PATH so git cannot be found
original_path = os.environ.get('PATH', '')
try:
    os.environ['PATH'] = ''
    result = _get_head_commit(os.getcwd())
    # actual (buggy) output: FileNotFoundError propagates
except FileNotFoundError:
    # Bug: exception propagated instead of returning None
    pass  # expected (correct) output: None
finally:
    os.environ['PATH'] = original_path
```

---

## Probe Script

```python
import sys
import os

try:
    from src.git import _get_head_commit
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Use current working directory as proj_dir — it exists and is a git repo.
# The bug is about exception propagation when git is not found, not about
# whether the directory is a valid repo.
proj_dir = os.getcwd()

# Save original PATH and set it to empty so git cannot be found.
# subprocess.run will raise FileNotFoundError, which _get_head_commit
# does NOT catch (it only catches CalledProcessError).
original_path = os.environ.get('PATH', '')
exception_raised = None
actual_return = None

try:
    os.environ['PATH'] = ''
    actual_return = _get_head_commit(proj_dir)
except FileNotFoundError as e:
    exception_raised = ('FileNotFoundError', str(e))
except Exception as e:
    exception_raised = (type(e).__name__, str(e))
finally:
    os.environ['PATH'] = original_path

if exception_raised:
    exc_type, exc_msg = exception_raised
    print(f'CONFIRMED — {exc_type} propagated: {exc_msg}. '
          f'Spec requires None return for all failures, but only CalledProcessError is caught.')
elif actual_return is None:
    print('NOT CONFIRMED — function returned None (exception was handled)')
else:
    print(f'NOT CONFIRMED — function returned normally: {actual_return!r}')
```

### Probe Output

```
CONFIRMED — FileNotFoundError propagated: [Errno 2] No such file or directory: 'git'. Spec requires None return for all failures, but only CalledProcessError is caught.
```
