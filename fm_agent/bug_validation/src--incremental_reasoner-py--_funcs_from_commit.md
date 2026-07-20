# Bug Report: _funcs_from_commit

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/_funcs_from_commit.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict whose keys are function name strings and whose values are the corresponding
    full source text strings, extracted from the version of rel_path stored at old_commit_id
  - The returned dict is empty when the file at old_commit_id contains no extractable
    functions for the language identified by lang_key
  - No filesystem side effects persist after this function returns: any temporary file
    created during the call is removed before return, even when an exception is raised
  - Raises subprocess.CalledProcessError when old_commit_id is not a valid commit or rel_path
    does not exist at that commit

---

### Actual Behavior

Post-condition:
Natural language: The function returns a dictionary mapping each top-level function name to its source text, extracted from the file at `rel_path` as it exists in the commit `old_commit_id`. The file content is retrieved via `git show`, written to a temporary file with the suffix `{ext}`, and then passed to `extract_functions_from_file`. Regardless of success or failure (e.g., git command failure, file write error, extraction error), if the temporary file is created and its path is stored in `tmp_path`, that file is deleted in a `finally` block before the function exits. If the temporary file creation itself fails before assigning `tmp_path`, an exception is raised and no cleanup is needed (the file may not exist or may be left behind). On normal completion, the returned dictionary reflects the output of `dict(extract_functions_from_file(tmp_path, lang_key))`.
Formal logic: Let `T = "{old_commit_id}:{rel_path}"`. Define:
- `text = _git("show", T)`  may raise `CalledProcessError`.
- `tmp_path = None` initially.
- If a `NamedTemporaryFile` is successfully opened, its content becomes `text`, and `tmp_path` is assigned its file path. The `with` block ensures the file is closed but not deleted (`delete=False`).
- Then the `try` block executes `result = dict(extract_functions_from_file(tmp_path, lang_key))` and returns it.
- The `finally` block executes `os.unlink(tmp_path)` (if `tmp_path` is not None, the file is removed).

For a call to `_funcs_from_commit(rel_path, lang_key, ext)` with the given pre-conditions:
1. **Normal termination**: `result` is a dictionary such that `result = dict(extract_functions_from_file(tmp_path, lang_key))` where `tmp_path` contained the text from `git show T`. After the function returns, the file at `tmp_path` no longer exists (`os.unlink` succeeded).
2. **Exceptional termination** (any exception raised inside the `try` block or from `return`): The `finally` block still runs `os.unlink`...

---

## Code Evidence

Line 4: with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
Line 5:     tmp.write(text)
Line 7:         try:
Line 8:             return dict(extract_functions_from_file(tmp_path, lang_key))
Line 9:         finally:
Line 10:             os.unlink(tmp_path)

---

## Trigger Condition

The specification requires that any temporary file created during the call is removed before the function returns, even when an exception is raised. The code creates a temporary file and writes to it inside a with block, but only the subsequent extraction and return are wrapped by a try-finally that deletes the file. If an exception occurs during the write (e.g., an I/O error), the function exits without ever entering the try block, leaving the temporary file behind. This violates the guaranteed cleanup in the presence of exceptions.

---

## How to trigger the bug

The buggy control flow in `_funcs_from_commit` (line 353-362 of `src/incremental_reasoner.py`) is:

```python
def _funcs_from_commit(rel_path, lang_key, ext):
    text = _git("show", f"{old_commit_id}:{rel_path}")
    with tempfile.NamedTemporaryFile("w", suffix=f".{ext}", delete=False) as tmp:
        tmp.write(text)       # <-- if this raises OSError...
        tmp_path = tmp.name   # <-- ...this line is never reached
    try:                      # <-- ...this block is never entered
        return dict(extract_functions_from_file(tmp_path, lang_key))
    finally:
        os.unlink(tmp_path)   # <-- ...never executed, temp file leaks
```

When `tmp.write(text)` raises an exception (e.g. OSError from disk full or permission error):
1. The `with` statement's `__exit__` closes the file but does NOT delete it (because `delete=False`)
2. `tmp_path` is never assigned (the assignment on line 358 is skipped)
3. The `try`/`finally` block on lines 359-362 is never entered
4. The exception propagates out of the function, and the temp file remains on disk

### Inputs

| Parameter | Value |
|-----------|-------|
| `rel_path` | `"sample.py"` (a Python source file tracked in a git repo) |
| `lang_key` | `"python"` |
| `ext` | `"py"` |
| `old_commit_id` | a valid commit SHA where `rel_path` exists |

### Expected (spec-correct) Output

The temp file created by `NamedTemporaryFile` must be deleted before the function returns, even when `tmp.write()` raises an exception. No filesystem side effects should persist.

### Actual (buggy) Output

The temp file at `/tmp/tmp28zt5w3r.py` (or similar) remains on disk after the function exits via an exception from `tmp.write()`. The `os.unlink(tmp_path)` call in the `finally` block is never reached because the `try` block was never entered.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
# Ensure project root is on sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import tempfile as _tempfile_module
_original_NTF = _tempfile_module.NamedTemporaryFile

class _FailingNTF:
    """NamedTemporaryFile replacement: write() raises OSError."""
    def __init__(self, *args, **kwargs):
        self._real = _original_NTF(*args, **kwargs)
    def __enter__(self):
        inner = self._real.__enter__()
        self._path = inner.name
        return self._FailingFile(inner)
    def __exit__(self, *args):
        return self._real.__exit__(*args)
    class _FailingFile:
        def __init__(self, f): self._f = f; self.name = f.name
        def write(self, text): raise OSError("Simulated I/O error")
        def __getattr__(self, n): return getattr(self._f, n)

_tempfile_module.NamedTemporaryFile = _FailingNTF

from src.incremental_reasoner import _collect_changed_functions
_collect_changed_functions("<repo_dir>", "<old_commit_id>")

# actual (buggy) output: temp file at /tmp/tmpXXXXXX.py remains on disk
# expected (correct) output: no temp file remains
```

---

## Probe Script

```py
"""Probe: _funcs_from_commit temp file leak when tmp.write() raises OSError.

The spec claims: "No filesystem side effects persist after this function returns:
any temporary file created during the call is removed before return, even when
an exception is raised."

Bug: tmp.write(text) at line 357 is outside the try/finally that calls
os.unlink(tmp_path). If tmp.write() raises, tmp_path is never assigned,
try/finally is never entered, and the temp file is never deleted.

We exercise _funcs_from_commit indirectly through the public API
_collect_changed_functions, which calls it for changed files that exist
in the old commit.
"""
import sys
import os

# Ensure the project root is on sys.path so "from src.xxx import ..." works.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
import shutil
import subprocess
import tempfile as _tempfile_module

# ── global tracking ────────────────────────────────────────────────────
_created_temp_paths = []

# Save originals before patching
_original_NTF = _tempfile_module.NamedTemporaryFile


class _WriteFailingFile:
    """Wraps a real file object; delegates everything EXCEPT write(), which
    raises OSError. Preemptively writes "mock content" so the file exists
    on disk and can be detected as orphaned after the bug is triggered."""

    def __init__(self, real_file):
        self._file = real_file
        self.name = real_file.name
        real_file.write("mock content for probing\n")
        real_file.flush()

    def write(self, text):
        raise OSError("Simulated I/O error during tmp.write()")

    def __getattr__(self, name):
        return getattr(self._file, name)


class _FailingNTF:
    """NamedTemporaryFile replacement: return a wrapper whose write() fails."""

    def __init__(self, *args, **kwargs):
        self._real = _original_NTF(*args, **kwargs)

    def __enter__(self):
        inner = self._real.__enter__()
        path = inner.name
        _created_temp_paths.append(path)
        return _WriteFailingFile(inner)

    def __exit__(self, *args):
        return self._real.__exit__(*args)

    def __getattr__(self, name):
        return getattr(self._real, name)


# ── set up a temp git repo ────────────────────────────────────────────
repo_dir = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__) or ".",
        "_probe_repo__incremental_reasoner",
    )
)
shutil.rmtree(repo_dir, ignore_errors=True)
os.makedirs(repo_dir)

git_env = {
    **os.environ,
    "GIT_AUTHOR_NAME": "probe",
    "GIT_AUTHOR_EMAIL": "probe@test",
    "GIT_COMMITTER_NAME": "probe",
    "GIT_COMMITTER_EMAIL": "probe@test",
}

subprocess.run(["git", "-C", repo_dir, "init"], capture_output=True, env=git_env)

# Create a Python source file in the repo so it matches EXT_TO_LANG["py"] = "python"
sample_py = os.path.join(repo_dir, "sample.py")
with open(sample_py, "w") as f:
    f.write("def original():\n    return 1\n")

subprocess.run(["git", "-C", repo_dir, "add", "sample.py"], capture_output=True, env=git_env)
subprocess.run(
    ["git", "-C", repo_dir, "commit", "-m", "initial"],
    capture_output=True,
    env=git_env,
)
old_commit_id = subprocess.run(
    ["git", "-C", repo_dir, "rev-parse", "HEAD"],
    capture_output=True,
    text=True,
    env=git_env,
).stdout.strip()

# Modify the file so it appears as "changed" in diff.  _funcs_from_commit
# is only called when the path exists at old_commit_id, which it does.
with open(sample_py, "w") as f:
    f.write("def modified():\n    return 2\n")

# ── apply the monkey-patch ─────────────────────────────────────────────
_tempfile_module.NamedTemporaryFile = _FailingNTF

# ── import and call the public API ─────────────────────────────────────
exception_caught = None
try:
    from src.incremental_reasoner import _collect_changed_functions

    _collect_changed_functions(repo_dir, old_commit_id)
except Exception as e:
    exception_caught = e
finally:
    # Restore immediately so cleanup below uses the real NamedTemporaryFile
    _tempfile_module.NamedTemporaryFile = _original_NTF

# ── verdict ────────────────────────────────────────────────────────────
orphaned = [p for p in _created_temp_paths if os.path.exists(p)]

# Cleanup
if exception_caught is not None:
    exc_type_name = type(exception_caught).__name__
else:
    exc_type_name = "None"

shutil.rmtree(repo_dir, ignore_errors=True)
for p in _created_temp_paths:
    if os.path.exists(p):
        os.unlink(p)

if orphaned and exc_type_name != "None":
    print(
        "CONFIRMED — temp file(s) not deleted after write failure: "
        f"{orphaned!r}. Exception: {exc_type_name}: {exception_caught}"
    )
elif orphaned:
    print(
        f"CONFIRMED — temp file(s) orphaned even without exception: {orphaned!r}"
    )
elif exc_type_name == "None":
    print(
        "NOT CONFIRMED — no exception raised during probe execution"
    )
else:
    print(
        f"NOT CONFIRMED — all temp files deleted after exception "
        f"({exc_type_name}: {exception_caught})"
    )
```

### Probe Output

```
CONFIRMED — temp file(s) not deleted after write failure: ['/tmp/tmp28zt5w3r.py']. Exception: OSError: Simulated I/O error during tmp.write()
```
