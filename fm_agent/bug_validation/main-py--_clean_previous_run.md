# Bug Report: _clean_previous_run

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/main-py/_clean_previous_run.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If work_dir refers to an existing directory in the filesystem, that
    directory and all of its contents (files and subdirectories, recursively)
    are permanently removed.
  - If work_dir does not refer to an existing directory, no action is taken
    and the function returns without error.
  - No other filesystem paths outside of work_dir are affected.

---

### Actual Behavior

After the function call:
- If no exception occurs:
  - If `os.path.isdir(work_dir)` held before the call, then `work_dir` no longer exists (`os.path.exists(work_dir)` is False).
  - If `work_dir` was not a directory before the call, the existence status of the path remains unchanged from the precall state.
- If an exception is raised during removal (e.g., by `shutil.rmtree`), the directory may be left in an inconsistent or partially removed state (no guarantee about its existence).

Formally (assuming normal return):
  ( old(os.path.isdir(work_dir))   os.path.exists(work_dir) )
   (  old(os.path.isdir(work_dir))  ( os.path.exists(work_dir)  old(os.path.exists(work_dir)) ) ).

No explicit return value is produced (returns `None`).

---

## Code Evidence

Line 3: if os.path.isdir(work_dir):
Line 4: shutil.rmtree(work_dir)

---

## Trigger Condition

The code uses os.path.isdir, which returns True for symbolic links to directories. It then unconditionally calls shutil.rmtree on that path. However, shutil.rmtree raises an OSError when the top-level path is a symbolic link to a directory (since Python 3.3+), because it refuses to follow symlinks at the root. As a result, the target directory and its contents are not removed and an exception is propagated. This violates the specification, which requires that when work_dir refers to an existing directory, that directory and all its contents are permanently removed without error.

---

## How to trigger the bug

The function `_clean_previous_run` in `main.py` checks whether `work_dir` is a directory using `os.path.isdir()`, which follows symlinks. When `work_dir` is a symbolic link to a directory, `os.path.isdir()` returns `True`, and the function proceeds to call `shutil.rmtree()` on the symlink. However, Python 3.3+ explicitly prevents `shutil.rmtree()` from operating on symlinks at the top level, raising `OSError: Cannot call rmtree on a symbolic link`. The spec requires the directory to be removed, but the function instead propagates an exception.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A symbolic link pointing to an existing directory (e.g., `/tmp/bug_probe_target_XXXXXX_link` → `/tmp/bug_probe_target_XXXXXX`) |

### Expected (spec-correct) Output

The target directory and all its contents are permanently removed (function returns `None` without error).

### Actual (buggy) Output

`OSError: Cannot call rmtree on a symbolic link` is raised. The target directory and its contents are not removed.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from main import _clean_previous_run

# Create a real target directory
tmpdir = tempfile.mkdtemp(prefix="bug_probe_target_")
# Create a symlink pointing to it
symlink_path = tmpdir + "_link"
os.symlink(tmpdir, symlink_path, target_is_directory=True)

# This should remove the directory per spec, but raises OSError
_clean_previous_run(symlink_path)
# actual (buggy) output: OSError: Cannot call rmtree on a symbolic link
# expected (correct) output: None (directory removed, no error)
```

---

## Probe Script

```python
"""Probe script for bug: main-py--_clean_previous_run.

Bug: os.path.isdir returns True for symlinks to directories, but shutil.rmtree
refuses to follow symlinks at the top level and raises OSError (Python 3.3+).
The spec requires that when work_dir refers to an existing directory, it is
permanently removed — but a symlink-to-directory triggers an exception instead.
"""
import sys
import os
import tempfile

# Add repo root to path so 'main' can be imported
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
))

# Load via the module's public entry point
from main import _clean_previous_run

actual = None
expected = None
passed = False
tmpdir = None
symlink_path = None

try:
    # Create a real target directory
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_target_")
    # Place a file inside so we can verify removal
    probe_file = os.path.join(tmpdir, "probe.txt")
    with open(probe_file, "w") as f:
        f.write("test")

    # Create a symlink pointing to the target directory
    symlink_path = tmpdir + "_link"
    os.symlink(tmpdir, symlink_path, target_is_directory=True)

    # Call the function with the symlink path.
    # Spec says: "If work_dir refers to an existing directory ... that directory
    # and all of its contents are permanently removed."
    # The symlink refers to an existing directory (os.path.isdir returns True),
    # so the spec requires removal. But shutil.rmtree raises OSError on symlinks.
    _clean_previous_run(symlink_path)

    # If we reach here, no exception was raised.
    expected = "removed"
    actual = "removed (no exception)"
    # Bug is NOT confirmed — the function handled the symlink case
    passed = False

except OSError as e:
    # shutil.rmtree raised OSError — this is the BUG.
    # The spec says the directory should be removed, but an exception was raised.
    expected = "directory removed (spec requirement)"
    actual = f"OSError: {e}"
    passed = True  # Bug CONFIRMED

except Exception as e:
    expected = "directory removed (spec requirement)"
    actual = f"Unexpected exception: {type(e).__name__}: {e}"
    passed = False

finally:
    # Cleanup: remove the symlink if it still exists
    if symlink_path and os.path.islink(symlink_path):
        try:
            os.unlink(symlink_path)
        except OSError:
            pass
    # Remove the temp target directory
    if tmpdir and os.path.isdir(tmpdir):
        import shutil
        try:
            shutil.rmtree(tmpdir)
        except OSError:
            pass

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}")
```

### Probe Output

```
CONFIRMED — actual: 'OSError: Cannot call rmtree on a symbolic link' | expected: 'directory removed (spec requirement)'
```
