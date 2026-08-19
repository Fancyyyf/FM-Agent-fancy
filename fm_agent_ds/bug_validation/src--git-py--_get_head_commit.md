# Bug Report: _get_head_commit

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/git-py/_get_head_commit.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If proj_dir is a valid git repository with a HEAD commit reachable via rev-parse, returns the full hexadecimal SHA identifier of that commit as a non-empty string. If proj_dir is not a git repository or the git command fails for any reason (including a missing or corrupt HEAD), returns None.

---

### Actual Behavior

After execution, exactly one of the following holds: (1) the subprocess.run(...) call succeeds without raising CalledProcessError, returns a CompletedProcess with some stdout string s, and the function returns s.strip(); no side effect occurs. (2) the call raises subprocess.CalledProcessError, a logging.info message is emitted containing proj_dir, and the function returns None. (3) the call raises any other exception (e.g., OSError), that exception is propagated and the function does not return normally. proj_dir is not modified in any case.

---

## Code Evidence

Line 8: except subprocess.CalledProcessError:

---

## Trigger Condition

If git is not found, subprocess.run raises FileNotFoundError (or OSError), which is not caught. The exception propagates instead of returning None as required by the specification for any git command failure.

---

## How to trigger the bug

The function `_get_head_commit` catches only `subprocess.CalledProcessError` (line 8 of `src/git.py`). When the `git` binary is not installed on the system (or is not found on PATH), `subprocess.run` raises `FileNotFoundError` (a subclass of `OSError`). Since `FileNotFoundError` is not a subclass of `CalledProcessError`, the exception is not caught and propagates up the call stack instead of returning `None` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | /tmp/nonexistent_repo_for_test (any path — the git binary is the issue) |

### Expected (spec-correct) Output

`None` (spec says: "returns None" for any git command failure)

### Actual (buggy) Output

`FileNotFoundError` exception raised — the exception propagates instead of being caught and returning `None`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
from src.git import _get_head_commit

# Simulate git not found on the system
with patch("src.git.subprocess.run",
           side_effect=FileNotFoundError("[Errno 2] No such file: 'git'")):
    result = _get_head_commit("/some/path")
    # actual (buggy) output: FileNotFoundError raised
    # expected (correct) output: result is None
```

---

## Probe Script

```python
"""Probe script for bug: _get_head_commit does not catch FileNotFoundError when
git binary is not found, causing exception propagation instead of returning None
as the specification requires."""

import sys
from unittest.mock import patch


def main():
    try:
        from src.git import _get_head_commit
    except ImportError as e:
        print(f"ERROR: cannot import _get_head_commit: {e}")
        sys.exit(1)

    # Test the trigger condition: simulate git binary not found.
    # subprocess.run raises FileNotFoundError (subclass of OSError) when the
    # executable is not found. This is NOT caught by the current
    # except subprocess.CalledProcessError handler, so the exception should
    # propagate instead of returning None.
    bug_confirmed = False
    try:
        with patch("src.git.subprocess.run",
                   side_effect=FileNotFoundError("[Errno 2] No such file: 'git'")):
            result = _get_head_commit("/tmp/nonexistent_repo_for_test")
            # If we reach here, the exception was caught somehow (bug not confirmed)
            expected = None
            if result is not None:
                bug_confirmed = True
                print(f"CONFIRMED — actual: {result!r} | expected: {expected!r}")
            else:
                print(f"NOT CONFIRMED — returned None as expected (FileNotFoundError was handled)")
    except FileNotFoundError:
        # The bug is confirmed: FileNotFoundError propagated past the function
        # instead of being caught and returning None per spec.
        print("CONFIRMED — FileNotFoundError raised instead of returning None "
              "(spec: 'returns None' for any git command failure)")
        sys.exit(0)
    except OSError:
        # FileNotFoundError is a subclass of OSError. Catch OSError too in
        # case FileNotFoundError gets re-wrapped.
        print("CONFIRMED — OSError raised instead of returning None "
              "(spec: 'returns None' for any git command failure)")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
        sys.exit(1)

    if bug_confirmed:
        sys.exit(0)
    else:
        print("NOT CONFIRMED — exception was caught, bug not reproducible")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — FileNotFoundError raised instead of returning None (spec: 'returns None' for any git command failure)
```
