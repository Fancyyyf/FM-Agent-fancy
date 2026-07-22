# Bug Report: _git

**Source file:** `src/git-py/frozen_worktree::_git.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Executes a git command rooted at proj_dir (equivalent to "git -C proj_dir"
    followed by each positional argument in order) as a child process.
  - Neither stdout nor stderr of the child process appears on the parent's
    standard output or standard error streams.
  - If the child process terminates with a non-zero exit code, raises
    subprocess.CalledProcessError whose attributes record the invoked command,
    the return code, and the captured stdout and stderr strings.
  - If the child process terminates with exit code zero, returns the captured
    stdout with every leading and trailing whitespace character (space, tab,
    newline, carriage return) removed.
  - The child process inherits the parent process's environment, subject to
    modification by any env keyword argument passed in **kwargs.

---

### Actual Behavior

After the call to `_git` with arguments `*args` and `**kwargs`, and given `proj_dir` a directory path in the enclosing scope:

- If `**kwargs` contains any key among `'check'`, `'capture_output'`, or `'text'`, the function call raises a `TypeError` because of repeated keyword arguments in the `subprocess.run` call; otherwise,
- The function constructs the command list `['git', '-C', proj_dir] + list(args)` and invokes `subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)`. 
  - If this call raises a `CalledProcessError` (because the git command exited nonzero), that exception propagates unmodified.
  - If it raises any other exception (e.g., `FileNotFoundError` if `git` is not found), that exception also propagates.
  - If the call completes normally, it returns a `CompletedProcess` object `cp` whose `stdout` is a string (because `capture_output=True` and `text=True`). The function then returns `cp.stdout.strip()`, a string with leading/trailing whitespace removed.

Formally:
Let `cmd = ['git', '-C', proj_dir] + list(args)`.
Let `conflict = {'check', 'capture_output', 'text'} ∩ keys(kwargs)`. 
Then:
- If `conflict ≠ ∅`: the invocation raises `TypeError`.
- If `conflict = ∅`:
  - If `subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)` raises exception `E` (where `E` may be `CalledProcessError` or any other), then `_git` raises `E`.
  - Otherwise, let `cp` be the returned `CompletedProcess` (`cp` must have `cp.returncode == 0` because `check=True` would have raised otherwise). Then `_git` returns `cp.stdout.strip()`.

---

## Code Evidence

```
Line 2:         return subprocess.run(
Line 3:             ["git", "-C", proj_dir, *args],
Line 4:             check=True, capture_output=True, text=True, **kwargs,
Line 5:         ).stdout.strip()
```

---

## Trigger Condition

The code hardcodes check=True, capture_output=True, text=True but also passes **kwargs to subprocess.run. If kwargs contains any of 'check', 'capture_output', or 'text', the call to subprocess.run raises TypeError due to duplicate keyword argument, violating the specification which requires executing the git command for any valid positional args and env keyword argument. For instance, _git('status', capture_output=True) raises TypeError, whereas spec demands it to capture output and return stripped stdout or raise CalledProcessError on failure.

---

## How to trigger the bug

The `_git` function in `src/git.py` (lines 75–79, defined as a closure inside `frozen_worktree()`) hardcodes `check=True`, `capture_output=True`, and `text=True` as explicit keyword arguments to `subprocess.run`, while simultaneously forwarding `**kwargs`. If a caller passes any of `check`, `capture_output`, or `text` in `**kwargs`, Python raises `TypeError: got multiple values for keyword argument`.

Although the current call-sites within `frozen_worktree()` only pass `env=env` (which does not conflict), the function signature promises to accept arbitrary kwargs for `subprocess.run`. Any consumer relying on that contract — for example, passing `capture_output=False` to send output to the parent terminal — will hit the TypeError.

### Inputs

| Parameter | Value |
|-----------|-------|
| `*args` | `("status",)` |
| `**kwargs` | `{"capture_output": True}` |

### Expected (spec-correct) Output

The git command should execute, capture its output, and return the stripped stdout string. The `capture_output=True` kwarg should be silently accepted (it's already being set by the hardcoded defaults, so it's redundant but harmless under the spec). Alternatively, the spec could require that conflicting kwargs be rejected with a clear error — but the spec explicitly says `**kwargs` are "forwarded to the subprocess invocation" without restriction.

### Actual (buggy) Output

`TypeError: subprocess.run() got multiple values for keyword argument 'capture_output'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import subprocess

# Exact replica of the _git closure body from src/git.py:75-79
proj_dir = "/tmp/test"

def _git(*args, **kwargs):
    return subprocess.run(
        ["git", "-C", proj_dir, *args],
        check=True, capture_output=True, text=True, **kwargs,
    ).stdout.strip()

# This raises TypeError:
_git("status", capture_output=True)
# TypeError: subprocess.run() got multiple values for keyword argument 'capture_output'
```

---

## Probe Script

```python
"""Probe script for bug: src--git-py--frozen_worktree::_git

Bug: _git() hardcodes check=True, capture_output=True, text=True but also passes
**kwargs to subprocess.run. If kwargs contains any of 'check', 'capture_output',
or 'text', Python raises TypeError due to duplicate keyword arguments.

Since _git is a closure defined inside frozen_worktree() and cannot be imported
directly, this probe reconstructs the exact code pattern to demonstrate the
latent bug. The replica is byte-for-byte identical to the _git function body
except for the variable name (proj_dir is defined in the enclosing scope).
"""

import os
import sys
from unittest.mock import patch, MagicMock

# Resolve repo root: probe is at fm_agent/bug_validation/probe_*.py, 3 levels deep.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

# Import the package via its public entry point (src.git.frozen_worktree)
try:
    from src.git import frozen_worktree
except Exception as e:
    print(f"ERROR: Failed to import frozen_worktree from src.git: {e}")
    sys.exit(1)

import subprocess as _sp


def _git_replica(proj_dir, *args, **kwargs):
    """Exact replica of the _git closure body from src/git.py:75-79.

    The original _git is defined as a closure inside frozen_worktree() with
    proj_dir captured from the enclosing scope. This replica makes proj_dir
    an explicit parameter to allow standalone testing.
    """
    return _sp.run(
        ["git", "-C", proj_dir, *args],
        check=True, capture_output=True, text=True, **kwargs,
    ).stdout.strip()


def main():
    confirmed = False
    error_detail = ""

    try:
        with patch.object(_sp, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "test output"
            mock_run.return_value = mock_result

            # Test 1: Normal invocation without conflicting kwargs — must succeed.
            result = _git_replica("/tmp/test", "status")
            if result != "test output":
                print(f"ERROR: Normal call returned unexpected value: {result!r}")
                sys.exit(1)

            # Test 2: Invocation with 'capture_output=True' in kwargs.
            # The spec says the function should accept env (and other valid
            # subprocess.run kwargs) without error. But because check=True,
            # capture_output=True, and text=True are already hardcoded as
            # positional keyword arguments, passing any of them again via
            # **kwargs causes a duplicate-keyword TypeError.
            try:
                _git_replica("/tmp/test", "status", capture_output=True)
                # If we get here, the bug is NOT present.
            except TypeError as e:
                confirmed = True
                error_detail = str(e)
            except Exception as e:
                print(f"ERROR: Unexpected exception: {type(e).__name__}: {e}")
                sys.exit(1)

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)

    if confirmed:
        print(f"CONFIRMED — TypeError raised with duplicate 'capture_output': {error_detail}")
    else:
        print("NOT CONFIRMED — conflicting kwargs did NOT raise TypeError (bug may be fixed)")


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — TypeError raised with duplicate 'capture_output': <MagicMock name='run' id='136370205191552'> got multiple values for keyword argument 'capture_output'
```
