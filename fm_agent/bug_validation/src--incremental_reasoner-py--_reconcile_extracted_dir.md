# Bug Report: _reconcile_extracted_dir

**Source file:** `fm_agent/extracted_functions/src/incremental_reasoner-py/_reconcile_extracted_dir.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Let (func_dir, ext) be the pair that maps abs_src to the extracted-functions
    directory and source extension via the same naming convention used by
    run_extraction. If func_dir is not an existing directory on disk, no
    filesystem changes occur and the function returns.
  - Otherwise, the set of expected extracted-function files for abs_src is
    determined:
    * When abs_src exists on disk and its file extension maps to a language
      recognized by the project's language registry, the expected files are
      derived from the current function spans of abs_src. Each span's
      deduplicated identifier forms an expected filename: the identifier
      suffixed with ".<ext>" when ext is non-empty, or the bare identifier
      when ext is empty. The span boundaries are computed with the same
      backend (codegraph when it indexes the file, otherwise regex) that
      run_extraction uses.
    * When abs_src does not exist on disk, or when its extension is not
      recognized, the set of expected files is empty.
  - Every file reachable by recursively walking func_dir whose absolute path
    does not match an expected file path is deleted. Expected files are
    preserved with their contents unchanged.
  - After file deletion, every subdirectory of func_dir — excluding func_dir
    itself — that contains neither files nor subdirectories is removed.

---

### Actual Behavior

If an exception is raised during `os.remove` or `os.rmdir`, the function terminates with that exception; the filesystem is left partially modified (some deletions performed up to the point of failure). Under normal termination (no exception), the following holds: Let (fd, ext) = _src_rel_to_func_dir(proj_dir, abs_src). If fd is not a directory before the call, the filesystem is unchanged. Otherwise, let lang = EXT_TO_LANG.get(ext); let Valid =  if lang is None or abs_src is not a file in the prestate, else { os.path.abspath(os.path.join(fd, ident) + ('.' + ext if ext else '')) | ident  { name | (name, _, _)  _function_spans(abs_src, lang, proj_dir) } }. Define Keep = { p | pre.file(p)  p  Valid }. After the call, for any path p: (files) if p is under fd then post.file(p)  p  Keep; else post.file(p)  pre.file(p). (directories) if p is under fd and p  fd then post.dir(p)  (pre.dir(p)  q  Keep such that p is a proper ancestor of q); if p = fd then post.dir(p) holds; if p is not under fd then post.dir(p)  pre.dir(p). (No empty subdirectory under fd except possibly fd itself remains; directories outside fd are untouched.)

---

## Code Evidence

Line 26: os.remove(abs_path)

---

## Trigger Condition

Specification B requires that every non-expected file under func_dir is deleted. When os.remove raises an exception (e.g., PermissionError), the function terminates immediately, leaving the non-expected file 'stale.py' on disk. This violates the specification because the required deletion did not complete.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | Temporary project directory (`/tmp/...`) |
| `abs_src` | A dummy source file with `.txt` extension (not in `EXT_TO_LANG` → valid set empty) |
| `func_dir` | Controlled temp directory containing two orphaned files |

### Expected (spec-correct) Output

All non-expected files under `func_dir` are deleted. The function either handles the PermissionError gracefully (continuing to delete other files) or ensures no partial state is left behind.

### Actual (buggy) Output

`PermissionError` is raised when `os.remove()` fails on `stale_undeletable.txt` (file in a read-only subdirectory). The function terminates immediately. The filesystem is left in a **partial state**: `stale_deletable.txt` is already deleted, but `stale_undeletable.txt` remains on disk.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, stat, tempfile, shutil

sys.path.insert(0, ".")
import src.incremental_reasoner as _incr

tmp = tempfile.mkdtemp()
func_dir = os.path.join(tmp, "func_dir")
os.makedirs(func_dir)

# Deletable file
with open(os.path.join(func_dir, "stale_deletable.txt"), "w") as f:
    f.write("x")

# Undeletable file in restricted subdir
restricted = os.path.join(func_dir, "restricted")
os.makedirs(restricted)
with open(os.path.join(restricted, "stale_undeletable.txt"), "w") as f:
    f.write("x")
os.chmod(restricted, stat.S_IRUSR | stat.S_IXUSR)

# Mock func_dir lookup
_incr._src_rel_to_func_dir = lambda _a, _b: (func_dir, "txt")

proj_dir = os.path.join(tmp, "proj")
os.makedirs(proj_dir)

# Trigger — raises PermissionError, filesystem left partial
_incr._reconcile_extracted_dir(proj_dir, os.path.join(proj_dir, "dummy.txt"))
# actual (buggy) output: PermissionError; stale_undeletable.txt still exists
# expected (correct) output: all orphaned files deleted, or no partial state
```

---

## Probe Script

```python
"""Probe for bug src--incremental_reasoner-py--_reconcile_extracted_dir.

Bug: _reconcile_extracted_dir uses plain os.remove() without exception handling.
When os.remove raises PermissionError on one file, the function terminates
immediately, leaving the filesystem in a partially modified state — some
non-expected files already deleted, others still present.
"""

import sys
import os
import stat
import shutil
import tempfile

# Ensure the repository root is on sys.path so we can import the package.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_TMP = None
_RESTRICTED_SUBDIR = None
_ORIGINAL_SRC_REL = None

try:
    import src.incremental_reasoner as _incr

    _ORIGINAL_SRC_REL = _incr._src_rel_to_func_dir

    # --- Set up temp workspace ---
    _TMP = tempfile.mkdtemp()
    _PROJ_DIR = os.path.join(_TMP, "proj")
    os.makedirs(_PROJ_DIR)

    _FUNC_DIR = os.path.join(_TMP, "func_dir")
    os.makedirs(_FUNC_DIR)

    # Deletable file in writable func_dir root.
    _STALE_DEL = os.path.join(_FUNC_DIR, "stale_deletable.txt")
    with open(_STALE_DEL, "w") as f:
        f.write("deletable content\n")

    # Restricted subdirectory → os.remove on files inside raises PermissionError.
    _RESTRICTED_SUBDIR = os.path.join(_FUNC_DIR, "restricted")
    os.makedirs(_RESTRICTED_SUBDIR)
    _STALE_UNDEL = os.path.join(_RESTRICTED_SUBDIR, "stale_undeletable.txt")
    with open(_STALE_UNDEL, "w") as f:
        f.write("must not be deleted\n")

    # Remove write permission: stat gives read + execute only.
    os.chmod(_RESTRICTED_SUBDIR, stat.S_IRUSR | stat.S_IXUSR)

    # Mock _src_rel_to_func_dir to return our controlled paths.
    _incr._src_rel_to_func_dir = lambda _pd, _src: (_FUNC_DIR, "txt")

    # Dummy source file.  "txt" is not in EXT_TO_LANG, so valid stays empty
    # and EVERY file under func_dir is a deletion target.
    _ABS_SRC = os.path.join(_PROJ_DIR, "dummy.txt")
    with open(_ABS_SRC, "w") as f:
        f.write("dummy\n")

    # --- Trigger the bug ---
    _raised = False
    try:
        _incr._reconcile_extracted_dir(_PROJ_DIR, _ABS_SRC)
    except PermissionError:
        _raised = True

    # --- Verify ---
    _undeletable_exists = os.path.exists(_STALE_UNDEL)
    _deletable_gone = not os.path.exists(_STALE_DEL)

    if _raised and _undeletable_exists and _deletable_gone:
        print(
            "CONFIRMED — PermissionError raised; stale_undeletable.txt remains "
            "on disk while stale_deletable.txt was already removed.  "
            "Filesystem left in partial state (deletion incomplete)."
        )
    elif _raised and not _undeletable_exists:
        print(
            "NOT CONFIRMED — PermissionError raised but stale_undeletable.txt "
            "was still deleted (unexpected)."
        )
    elif not _raised and _deletable_gone:
        print(
            "NOT CONFIRMED — function completed normally; all orphaned files "
            "were deleted."
        )
    else:
        print(
            "NOT CONFIRMED — unexpected state: raised=%s, "
            "undeletable_exists=%s, deletable_gone=%s"
            % (_raised, _undeletable_exists, _deletable_gone)
        )

except Exception as _exc:
    print("ERROR: %s" % _exc)
    sys.exit(1)

finally:
    # Restore mock.
    if _ORIGINAL_SRC_REL is not None:
        try:
            import src.incremental_reasoner as _incr2

            _incr2._src_rel_to_func_dir = _ORIGINAL_SRC_REL
        except Exception:
            pass

    # Restore write permission on the restricted subdir for cleanup.
    if _RESTRICTED_SUBDIR is not None and os.path.exists(_RESTRICTED_SUBDIR):
        os.chmod(_RESTRICTED_SUBDIR, stat.S_IRWXU)

    # Remove temp tree.
    if _TMP is not None and os.path.exists(_TMP):
        shutil.rmtree(_TMP, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — PermissionError raised; stale_undeletable.txt remains on disk while stale_deletable.txt was already removed.  Filesystem left in partial state (deletion incomplete).
```
