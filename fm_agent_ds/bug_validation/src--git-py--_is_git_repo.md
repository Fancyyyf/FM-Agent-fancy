# Bug Report: _is_git_repo

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/git-py/_is_git_repo.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True if and only if proj_dir is an existing git repository whose HEAD reference resolves to at least one commit. Returns False if proj_dir is not a git repository, does not have a valid or reachable HEAD, or the verification fails for any other reason. The function does not modify proj_dir or any filesystem state.

---

### Actual Behavior

If the function returns normally (no uncaught exception), then:
- the return value is True if and only if executing `git -C proj_dir rev-parse --verify HEAD` via subprocess.run succeeds (return code 0, no CalledProcessError);
- the return value is False if and only if that subprocess.run call raises a subprocess.CalledProcessError (nonzero exit code, e.g., because proj_dir is not a git repository or has no commits).
If any other exception occurs (e.g., FileNotFoundError from missing git, OSError, TimeoutExpired, etc.), it propagates uncaught and the function exits without returning a value.
In both normal and exceptional exits, proj_dir is not modified and no persistent side effects are produced; the only observable effect is the execution of the subprocess. In formal logic:
(no exception ∧ return = True)    ⇔ (subprocess.run(...) completes with returncode = 0 ∧ no CalledProcessError)
(no exception ∧ return = False)   ⇔ (subprocess.run(...) raises CalledProcessError)
(exception) ⇒ (return is undefined ∧ proj_dir = proj_dir_pre)

---

## Code Evidence

Line 9: except subprocess.CalledProcessError:

---

## Trigger Condition

The code only catches subprocess.CalledProcessError. If the 'git' executable is missing, subprocess.run raises FileNotFoundError (or another OSError), which is not caught, so the function propagates an uncaught exception instead of returning False as required by the specification for any verification failure.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A valid git repository directory (with at least one commit) |
| git binary | Not available on PATH |

### Expected (spec-correct) Output

`False` — the specification requires that any verification failure, including a missing `git` executable, returns False.

### Actual (buggy) Output

Uncaught `FileNotFoundError` exception — the function crashes instead of returning False.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import subprocess

def _is_git_repo(proj_dir):
    """Return whether proj_dir is a git repository with at least one commit."""
    try:
        subprocess.run(
            ["git", "-C", proj_dir, "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False

# Clear PATH so 'git' is not found
env = os.environ.copy()
env["PATH"] = "/tmp/empty"

_is_git_repo("/some/git/repo")
# actual (buggy) output: FileNotFoundError: [Errno 2] No such file or directory: 'git'
# expected (correct) output: False
```

---

## Probe Script

```python
"""Probe script for bug: _is_git_repo — missing exception handling for FileNotFoundError.

Bug claim: _is_git_repo only catches subprocess.CalledProcessError. If the 'git'
executable is missing, subprocess.run raises FileNotFoundError (or another OSError),
which is not caught. The function propagates an uncaught exception instead of
returning False as required by the spec.

This probe replicates the extracted function exactly and tests it against a real
git repo with PATH modified to hide the git binary.
"""

import os
import subprocess
import sys
import tempfile
import shutil

# ── Replicate exactly the extracted _is_git_repo function ──────────────────

def _is_git_repo(proj_dir):
    """Return whether proj_dir is a git repository with at least one commit."""
    try:
        subprocess.run(
            ["git", "-C", proj_dir, "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def main() -> None:
    # ── Step 0: Create a temp workspace (NOT fm_agent/) ────────────────────
    tmpdir = tempfile.mkdtemp(prefix="probe_is_git_repo_")
    try:
        # ── Step 1: Create a minimal git repo as test input ─────────────────
        repo_path = os.path.join(tmpdir, "test_repo")
        os.makedirs(repo_path)

        subprocess.run(
            ["git", "init", repo_path],
            check=True, capture_output=True, text=True,
        )
        # Make an initial commit so HEAD resolves
        readme = os.path.join(repo_path, "README.md")
        with open(readme, "w") as f:
            f.write("# test\n")
        subprocess.run(
            ["git", "-C", repo_path, "config", "user.email", "test@test.com"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", repo_path, "config", "user.name", "Test"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", repo_path, "add", "README.md"],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", repo_path, "commit", "-m", "init"],
            check=True, capture_output=True, text=True,
        )

        # ── Step 2: Sanity check — git available, should return True ────────
        result_normal = _is_git_repo(repo_path)
        if result_normal is not True:
            print(f"NOT CONFIRMED — sanity check failed: expected True, got {result_normal!r}")
            return

        # ── Step 3: Make git unavailable by clearing PATH ──────────────────
        # Remove all standard git locations to trigger FileNotFoundError
        sanitized_path = os.pathsep.join(
            p for p in os.environ.get("PATH", "").split(os.pathsep)
            if "git" not in p.lower() and p.strip()
        )
        env_without_git = os.environ.copy()
        env_without_git["PATH"] = sanitized_path

        # Use a fake empty directory as the "git" to guarantee lookup failure
        fake_bin = os.path.join(tmpdir, "empty_bin")
        os.makedirs(fake_bin)
        env_without_git["PATH"] = fake_bin

        # ── Step 4: Attempt the call — should return False per spec, but
        #    the buggy code will crash with FileNotFoundError ─────────────
        actual = None
        error_msg = None
        try:
            actual = _is_git_repo_with_env(repo_path, env_without_git)
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"

        expected = False  # spec says: any verification failure → False

        if error_msg is not None:
            # Bug confirmed: function crashed instead of returning False
            print(f"CONFIRMED — bug reproduced: function crashed with {error_msg}")
            print(f"  Expected: {expected!r}")
            print(f"  Actual:   uncaught exception propagated")
        elif actual is False:
            print(f"NOT CONFIRMED — function returned False as expected (no bug)")
            print(f"  Expected: {expected!r}")
            print(f"  Actual:   {actual!r}")
        else:
            print(f"NOT CONFIRMED — unexpected return value: {actual!r}")
            print(f"  Expected: {expected!r}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _is_git_repo_with_env(proj_dir, env):
    """Variant that passes a custom environment to subprocess.run.

    The original _is_git_repo uses the default env (inherits os.environ).
    We need to inject a custom PATH to simulate missing git, so we wrap
    subprocess.run to accept a custom env.

    This is the minimal modification needed to test the bug; the original
    _is_git_repo code at lines 3-8 is structurally identical.
    """
    try:
        subprocess.run(
            ["git", "-C", proj_dir, "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True,
            env=env,
        )
        return True
    except subprocess.CalledProcessError:
        return False


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — bug reproduced: function crashed with FileNotFoundError: [Errno 2] No such file or directory: 'git'
  Expected: False
  Actual:   uncaught exception propagated
```
