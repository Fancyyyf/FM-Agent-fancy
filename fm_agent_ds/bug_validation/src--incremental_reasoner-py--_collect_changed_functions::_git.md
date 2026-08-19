# Bug Report: _git

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_collect_changed_functions::_git.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Executes the command git -C proj_dir <args> in a subprocess and returns the captured standard output as a string. Raises subprocess.CalledProcessError when the git command exits with a non-zero status code; the captured standard error is available in the exception's stderr attribute.

---

### Actual Behavior

If the function returns normally, it returns the captured stdout (as a string) of the command `git -C proj_dir *args`. If the git subprocess terminates with a non-zero exit code, a `subprocess.CalledProcessError` is raised. If the `git` executable cannot be found, a `FileNotFoundError` (a subclass of `OSError`) is raised. No other side effects on the Python process state occur, although the git command may modify the repository and file system.

Formally: post  { normal_return   res  subprocess.CompletedProcess . res = subprocess.run(['git', '-C', proj_dir, *args], check=True, capture_output=True, text=True)  res.returncode = 0  return = res.stdout }  { exceptional  (exception  {subprocess.CalledProcessError, FileNotFoundError}) }

---

## Code Evidence

Line 5: text=True

---

## Trigger Condition

The specification requires that when the git command exits with code 0, the function returns the captured standard output as a string. Using text=True without error handling can raise UnicodeDecodeError for binary stdout, violating the return-type guarantee.

---

## How to trigger the bug

The nested helper `_git` inside `_collect_changed_functions` uses `subprocess.run(..., text=True)` to decode git stdout as text. When `_funcs_from_commit` calls `_git("show", f"{commit}:{rel_path}")` on a file whose committed blob contains binary data (non-UTF-8 bytes), `text=True` raises `UnicodeDecodeError` instead of returning a string, which the specification does not account for.

### Inputs

| Parameter | Value |
|---|---|
| `proj_dir` | A git repository containing a committed file with a recognized source extension (e.g. `.py`) whose blob content is binary |
| `old_commit_id` | A commit where the binary file exists and has since been modified in the working tree |
| `*args` (via `_funcs_from_commit`) | `"show"`, `"HEAD:crash.py"` (path to binary file) |

### Expected (spec-correct) Output

A string (the decoded content), or `subprocess.CalledProcessError` if non-zero exit code, or `FileNotFoundError` if git not found.

### Actual (buggy) Output

`UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80 in position 0: invalid start byte`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, sys, shutil, tempfile, subprocess

sys.path.insert(0, os.getcwd())
from src.incremental_reasoner import _collect_changed_functions

work_dir = tempfile.mkdtemp()
proj_dir = os.path.join(work_dir, "test_repo")
os.makedirs(proj_dir)
subprocess.run(["git", "-C", proj_dir, "init", "--quiet"], check=True, capture_output=True)
subprocess.run(["git", "-C", proj_dir, "config", "user.email", "t@t.com"], check=True, capture_output=True)
subprocess.run(["git", "-C", proj_dir, "config", "user.name", "T"], check=True, capture_output=True)

# Commit a binary .py file
with open(os.path.join(proj_dir, "crash.py"), "wb") as f:
    f.write(b'\x80\x81\x82\x83\xff\xfe\xfd\xfc\nprint("x")')
subprocess.run(["git", "-C", proj_dir, "add", "crash.py"], check=True, capture_output=True)
subprocess.run(["git", "-C", proj_dir, "commit", "-m", "init", "--quiet"], check=True, capture_output=True)

# Modify (unstaged) so diff picks it up
with open(os.path.join(proj_dir, "crash.py"), "wb") as f:
    f.write(b'\x80\x81\x82\x83\xff\xfe\xfd\xfc\x00\nprint("x")')

# Triggers UnicodeDecodeError inside _git("show", "HEAD:crash.py")
_collect_changed_functions(proj_dir, "HEAD")
# actual (buggy) output: UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80 in position 0
# expected (correct) output: should handle binary stdout gracefully or document UnicodeDecodeError

shutil.rmtree(work_dir, ignore_errors=True)
```

---

## Probe Script

```python
"""Probe: UnicodeDecodeError in _collect_changed_functions::_git via text=True.

The nested helper _git() uses subprocess.run(..., text=True) without error
handling for binary stdout. This probe creates a temp git repo with a binary
.py file and calls _collect_changed_functions to exercise _git("show", ...)
which will try to decode binary blob content as text.

IMPORTANT: All work happens in a temporary directory outside fm_agent/.
The only output is the CONFIRMED/NOT CONFIRMED line on stdout.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import traceback


def main():
    # script is at repo_root/fm_agent/bug_validation/probe_xxx.py
    # Walk up: probe → bug_validation → fm_agent → repo_root (3 levels)
    repo_root = os.path.abspath(__file__)
    for _ in range(3):
        repo_root = os.path.dirname(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    work_dir = tempfile.mkdtemp(prefix="bug_probe_")
    got_confirmed = False
    last_error = None

    try:
        # ── Setup: a git repo with a binary .py file ──
        proj_dir = os.path.join(work_dir, "test_repo")
        os.makedirs(proj_dir)

        _run(["git", "-C", proj_dir, "init", "--quiet"])
        _run(["git", "-C", proj_dir, "config", "user.email", "test@test.com"])
        _run(["git", "-C", proj_dir, "config", "user.name", "Test"])

        # Create a binary file with a .py extension.
        # Bytes 0x80-0xFF: every single byte is an invalid UTF-8 start byte,
        # so text=True decoding WILL fail regardless of locale.
        binary_file = os.path.join(proj_dir, "crash.py")
        with open(binary_file, "wb") as f:
            f.write(b'\x80\x81\x82\x83\xff\xfe\xfd\xfc\nprint("this is not valid Python")')

        _run(["git", "-C", proj_dir, "add", "crash.py"])
        _run(["git", "-C", proj_dir, "commit", "-m", "initial commit", "--quiet"])

        # Modify the file (unstaged change) so diff picks it up.
        with open(binary_file, "wb") as f:
            f.write(b'\x80\x81\x82\x83\xff\xfe\xfd\xfc\x00\nprint("modified")')

        # ── Exercise the buggy code path ──
        from src.incremental_reasoner import _collect_changed_functions

        try:
            _collect_changed_functions(proj_dir, "HEAD")
            # If we get here, no UnicodeDecodeError was raised.
            # Either the code path didn't exercise _git("show", ...) (e.g. CodeGraph
            # was used) or the file content happened to decode without error.
        except UnicodeDecodeError as exc:
            got_confirmed = True
            print(f"CONFIRMED - UnicodeDecodeError: {exc}")
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"NOT CONFIRMED - unexpected error: {last_error}")
            traceback.print_exc()
            return

        # ── Attempt 2: try a more explicitly invalid UTF-8 sequence ──
        proj_dir2 = os.path.join(work_dir, "test_repo2")
        os.makedirs(proj_dir2)
        _run(["git", "-C", proj_dir2, "init", "--quiet"])
        _run(["git", "-C", proj_dir2, "config", "user.email", "test@test.com"])
        _run(["git", "-C", proj_dir2, "config", "user.name", "Test"])

        binary_file2 = os.path.join(proj_dir2, "crash2.py")
        with open(binary_file2, "wb") as f:
            f.write(b'\xff\xfe\x00\x00\xde\xad\xbe\xef')
        _run(["git", "-C", proj_dir2, "add", "crash2.py"])
        _run(["git", "-C", proj_dir2, "commit", "-m", "initial", "--quiet"])

        with open(binary_file2, "wb") as f:
            f.write(b'\xff\xfe\x00\x00\xde\xad\xbe\xef\x00')

        try:
            _collect_changed_functions(proj_dir2, "HEAD")
        except UnicodeDecodeError as exc:
            got_confirmed = True
            print(f"CONFIRMED - UnicodeDecodeError (attempt 2): {exc}")
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"NOT CONFIRMED - unexpected error (attempt 2): {last_error}")
            traceback.print_exc()
            return

        # ── Attempt 3: test the vulnerable pattern directly ──
        proj_dir3 = os.path.join(work_dir, "test_repo3")
        os.makedirs(proj_dir3)
        _run(["git", "-C", proj_dir3, "init", "--quiet"])
        _run(["git", "-C", proj_dir3, "config", "user.email", "test@test.com"])
        _run(["git", "-C", proj_dir3, "config", "user.name", "Test"])

        binary_file3 = os.path.join(proj_dir3, "crash3.py")
        with open(binary_file3, "wb") as f:
            f.write(bytes(range(256)))
        _run(["git", "-C", proj_dir3, "add", "crash3.py"])
        _run(["git", "-C", proj_dir3, "commit", "-m", "initial", "--quiet"])

        with open(binary_file3, "wb") as f:
            f.write(bytes(range(256)) + b'\x00')

        try:
            _collect_changed_functions(proj_dir3, "HEAD")
        except UnicodeDecodeError as exc:
            got_confirmed = True
            print(f"CONFIRMED - UnicodeDecodeError (attempt 3): {exc}")
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"NOT CONFIRMED - unexpected error (attempt 3): {last_error}")
            traceback.print_exc()
            return

        # All 3 attempts failed to confirm.
        print("NOT CONFIRMED - could not reproduce UnicodeDecodeError after 3 attempts")

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _run(cmd):
    """Run a command, check exit code, suppress output."""
    subprocess.run(cmd, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
WARNING:root:CodeGraph could not provide both revisions for crash.py; using legacy regex comparison.
CONFIRMED - UnicodeDecodeError: 'utf-8' codec can't decode byte 0x80 in position 0: invalid start byte
```
