# Bug Report: _git

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/git-py/frozen_worktree::_git.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Executes git -C proj_dir with the arguments provided in args as a subprocess and returns the captured stdout with surrounding whitespace removed. By default, raises subprocess.CalledProcessError when the git subprocess exits with a non-zero status; this error behavior is overridable via kwargs. By default, stdout and stderr are captured and decoded as text; both defaults are overridable via kwargs.

---

### Actual Behavior

If the system git executable is available in the PATH and the subprocess command `git -C <proj_dir> <args>` executes successfully (exit code 0), the function returns a string containing the stripped standard output of that command. If the command executes but exits with a non-zero code, a `subprocess.CalledProcessError` is raised. If the git executable cannot be found or executed (e.g., not installed), an `OSError` (specifically `FileNotFoundError` on POSIX) is raised. The function performs no other side effects on the calling program's state. Formal logic: Let `cmd = ["git", "-C", proj_dir] + list(args)` and `env` denote the execution environment. The post-condition is: ( out: subprocess.CompletedProcess such that out.returncode = 0  return = out.stdout.strip())  ( exc: CalledProcessError such that exc.returncode  0  exc.cmd = cmd  raised(exc))  ( exc: FileNotFoundError (or OSError) such that raised(exc)).

---

## Code Evidence

Line 2-5: subprocess.run(...).stdout.strip()

---

## Trigger Condition

The specification states that the default for capturing stdout is overridable via kwargs. If a caller overrides capture_output=False, the function attempts to access .stdout.strip() on the returned CompletedProcess, but .stdout is None, raising an AttributeError. This violates the specification because the function does not properly handle the overridden default.

---

## How to trigger the bug

The `capture_output=True` default is hardcoded as a positional keyword argument in the `subprocess.run()` call. When a caller passes `capture_output=False` (or any kwarg that conflicts with the hardcoded defaults) via `**kwargs`, Python raises `TypeError: subprocess.run() got multiple values for keyword argument 'capture_output'` because the same keyword argument is specified twice. The specification promises that both `capture_output` and `text` defaults are overridable via `kwargs`, but the code prevents any override by hardcoding these values.

**Note on the trigger condition:** The original trigger condition describes an `AttributeError` (`.stdout` being `None` after overriding `capture_output=False`). In practice, the code fails earlier with a `TypeError` for duplicate keyword arguments, never reaching `.stdout.strip()`. Both errors confirm the same root cause: the hardcoded defaults prevent legitimate override attempts that the specification explicitly allows.

### Inputs

| Parameter | Value |
|-----------|-------|
| `*args` | `("rev-parse", "--verify", "HEAD")` (valid git command) |
| `**kwargs` | `{"capture_output": False}` (attempt to override the default) |

### Expected (spec-correct) Output

The function should accept `capture_output=False` as an override, execute the git command without capturing stdout (output goes to parent process), and return the stripped stdout. The specification says "both defaults are overridable via kwargs."

### Actual (buggy) Output

`TypeError: subprocess.run() got multiple values for keyword argument 'capture_output'` — the hardcoded `capture_output=True` clashes with the caller's `capture_output=False` override.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to a directory with a valid git repository.
2. Reconstruct the `_git` function pattern (same as `src/git.py` lines 75-79):

```python
import subprocess

proj_dir = "/path/to/your/repo"

def _git(*args, **kwargs):
    return subprocess.run(
        ["git", "-C", proj_dir, *args],
        check=True, capture_output=True, text=True, **kwargs,
    ).stdout.strip()

_git("rev-parse", "--verify", "HEAD", capture_output=False)
# actual (buggy) output: TypeError: subprocess.run() got multiple values for keyword argument 'capture_output'
# expected (correct) output: the captured stdout string (or None if not captured)
```

---

## Probe Script

```python
"""Probe script for bug: src--git-py--frozen_worktree::_git

The bug claim: _git() hardcodes capture_output=True in the subprocess.run()
call, but the specification states that this default is overridable via kwargs.
Passing capture_output=False (or any kwarg that conflicts with the hardcoded
capture_output=True) should be supported but fails.

This script reconstructs the exact _git function pattern (same as
src/git.py lines 75-79) inside a temporary git repo and verifies that
overriding the capture_output default via kwargs is impossible.
"""

import os
import sys
import shutil
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# Build a fresh temporary git repo so _git has a valid repo to operate on
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp(prefix="probe_git_")
repo_path = os.path.join(tmpdir, "repo")
os.makedirs(repo_path)

subprocess.run(["git", "-C", repo_path, "init"],
               check=True, capture_output=True, text=True)
subprocess.run(["git", "-C", repo_path, "config", "user.name", "probe"],
               check=True, capture_output=True, text=True)
subprocess.run(["git", "-C", repo_path, "config", "user.email", "p@p.com"],
               check=True, capture_output=True, text=True)

# Create a file and commit so there's a HEAD
with open(os.path.join(repo_path, "hello.txt"), "w") as f:
    f.write("hello")
subprocess.run(["git", "-C", repo_path, "add", "hello.txt"],
               check=True, capture_output=True, text=True)
subprocess.run(["git", "-C", repo_path, "commit", "-m", "initial"],
               check=True, capture_output=True, text=True)

# ---------------------------------------------------------------------------
# Reconstruct the exact _git function pattern (identical to src/git.py:75-79)
# ---------------------------------------------------------------------------
proj_dir = repo_path

def _git(*args, **kwargs):
    return subprocess.run(
        ["git", "-C", proj_dir, *args],
        check=True, capture_output=True, text=True, **kwargs,
    ).stdout.strip()

# ---------------------------------------------------------------------------
# Test 1: Normal operation (no conflicting kwargs) — should work fine
# ---------------------------------------------------------------------------
result = "ERROR"
detail = ""

try:
    # Sanity check: _git works normally without conflicting kwargs
    head = _git("rev-parse", "--verify", "HEAD")
    assert head, "Expected non-empty HEAD commit hash"

    # Now test the trigger condition: override capture_output via kwargs.
    # The spec says "both defaults are overridable via kwargs", but
    # capture_output=True is hardcoded. Passing capture_output=False
    # should either:
    #   (a) raise TypeError for duplicate keyword argument, OR
    #   (b) raise AttributeError because .stdout is None
    # Either outcome confirms the bug because the spec promises overridability.
    _git("rev-parse", "--verify", "HEAD", capture_output=False)

    # If we reach here, somehow no error occurred — bug not confirmed
    result = "NOT CONFIRMED"
    detail = "capture_output=False was accepted without error (unexpected)"

except TypeError as e:
    # Duplicate keyword: capture_output=True (hardcoded) AND
    # capture_output=False (from kwargs). Python forbids this.
    # This confirms the bug: the spec says the default is overridable,
    # but the code hardcodes it and prevents any override.
    result = "CONFIRMED"
    detail = (
        f"TypeError raised when passing capture_output=False via kwargs: {e} "
        "— spec says capture_output default is overridable, but the "
        "hardcoded capture_output=True prevents any override"
    )

except AttributeError as e:
    # .stdout.strip() on None — this confirms the bug from a different
    # angle: even if the subprocess ran without capturing, the function
    # blindly calls .strip() on potentially-None stdout.
    result = "CONFIRMED"
    detail = (
        f"AttributeError raised when .stdout was None: {e} "
        "— spec says capture_output default is overridable, but the "
        "function always calls .stdout.strip() without checking"
    )

except Exception as e:
    # Any other error (e.g., subprocess.CalledProcessError from git) is
    # an unexpected failure in the probe itself, not a reproduction.
    result = "ERROR"
    detail = f"Unexpected exception: {type(e).__name__}: {e}"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
print(f"{result} — {detail}")
```

### Probe Output

```
CONFIRMED — TypeError raised when passing capture_output=False via kwargs: subprocess.run() got multiple values for keyword argument 'capture_output' — spec says capture_output default is overridable, but the hardcoded capture_output=True prevents any override
```
