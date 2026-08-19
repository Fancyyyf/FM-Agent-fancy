# Bug Report: _trim_project_in_place

**Source file:** `src/entry_reasoning_pipeline-py/_trim_project_in_place.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

For every source file path key in all_by_source: if keep_by_source contains a non-empty set of function identifiers for that path, the file under proj_dir has been modified to contain only the function bodies corresponding to identifiers in that set plus all non-function lines; all functions whose identifiers appear in all_by_source but not in keep_by_source for that file have been removed from the file. If keep_by_source does not contain the path or contains an empty set for it, the file at that path under proj_dir has been deleted. Files whose paths do not appear as keys in all_by_source are left unchanged. Returns None.

---

### Actual Behavior

After execution, proj_dir's file system is updated: for each source_rel in sorted(all_by_source), let src_path = join(proj_dir, source_rel). If src_path was a regular file and keep_by_source contains a non-empty set for source_rel, then src_path remains as a regular file with modified content: only function definitions whose names are in keep_by_source[source_rel] are preserved, together with all non-function context lines (e.g., imports, comments, module-level code), maintaining original order; all other function definitions from all_by_source[source_rel] are removed. If src_path was a regular file and keep_by_source lacks source_rel or has an empty set, then src_path is deleted. If src_path was not a regular file, it is unchanged. Any file in proj_dir whose path is not a key in all_by_source is left untouched. total_kept and total_removed sum the kept and removed function counts from _trim_source_file calls, deleted_files counts the deleted files, and a summary message is printed.

---

## Code Evidence

Line 196: if not os.path.isfile(src_path):
Line 197:             continue

---

## Trigger Condition

The code only acts on entries in all_by_source if their path is a regular file (isfile). The specification unconditionally requires deletion when keep_by_source has no entry or an empty set for that key, and modification when it has a non-empty set. A dangling symlink is a valid file path but not a regular file, leading to a violation.

---

## How to trigger the bug

The `_trim_project_in_place` function uses `os.path.isfile()` as a guard (line 196–197 in `src/entry_reasoning_pipeline.py`). When a path in `all_by_source` is a dangling symlink (or any non-regular file), `os.path.isfile()` returns `False`, causing the function to `continue` past that entry without deleting or modifying the file. The specification makes no such exception — it requires every path in `all_by_source` to be processed unconditionally.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory containing `real.py` (regular file) and `dangling.py` (dangling symlink) |
| `all_by_source` | `{"real.py": {"foo"}, "dangling.py": {"bar"}}` |
| `keep_by_source` | `{}` (empty — signals both files should be deleted) |

### Expected (spec-correct) Output

Both `real.py` and `dangling.py` are deleted from `proj_dir`.

### Actual (buggy) Output

`real.py` is deleted, but `dangling.py` persists — `os.path.isfile()` returned `False` for the dangling symlink, so the function skipped it entirely.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from src.entry_reasoning_pipeline import _trim_project_in_place

tmpdir = tempfile.mkdtemp()
real_path = os.path.join(tmpdir, "real.py")
dangling_path = os.path.join(tmpdir, "dangling.py")

with open(real_path, "w") as f:
    f.write("def foo():\n    pass\n")

os.symlink(os.path.join(tmpdir, "nonexistent_target.py"), dangling_path)

all_by_source = {"real.py": {"foo"}, "dangling.py": {"bar"}}
keep_by_source = {}

_trim_project_in_place(tmpdir, all_by_source, keep_by_source)

print("real.py exists:", os.path.exists(real_path))        # actual: False
print("dangling.py exists:", os.path.lexists(dangling_path))  # actual (buggy): True
# expected (correct): both False
```

---

## Probe Script

```python
"""Probe for bug: _trim_project_in_place skips non-regular files (e.g. dangling
symlinks) due to os.path.isfile() guard at line 196, violating the spec which
requires unconditional deletion/modification for all paths in all_by_source.

Bug ID: src--entry_reasoning_pipeline-py--_trim_project_in_place

Expected (spec): A dangling symlink listed in all_by_source should be deleted
when keep_by_source has no entry for it.

Actual (bug): os.path.isfile() returns False for dangling symlinks, so the
function continues past without deleting or modifying the file.
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is importable so we can import from src.*
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

tmpdir = None

try:
    tmpdir = tempfile.mkdtemp(prefix="probe_trim_")
    real_path = os.path.join(tmpdir, "real.py")
    dangling_path = os.path.join(tmpdir, "dangling.py")

    with open(real_path, "w") as f:
        f.write("def foo():\n    pass\n")

    os.symlink(os.path.join(tmpdir, "nonexistent_target.py"), dangling_path)
    assert os.path.lexists(dangling_path), "symlink should exist"
    assert not os.path.isfile(dangling_path), "dangling symlink should NOT be a regular file"

    all_by_source = {
        "real.py": {"foo"},
        "dangling.py": {"bar"},
    }
    keep_by_source = {}

    from src.entry_reasoning_pipeline import _trim_project_in_place

    _trim_project_in_place(tmpdir, all_by_source, keep_by_source)

    real_exists = os.path.exists(real_path)
    dangling_exists = os.path.lexists(dangling_path)

    if not real_exists and dangling_exists:
        print(
            f"CONFIRMED — real.py was correctly deleted, "
            f"but dangling symlink 'dangling.py' was NOT deleted. "
            f"spec requires deletion for all all_by_source entries "
            f"when keep_by_source lacks them; "
            f"os.path.isfile() returned False for the dangling symlink "
            f"and the function incorrectly continued past it."
        )
    elif not real_exists and not dangling_exists:
        print(
            f"NOT CONFIRMED — both files were deleted; "
            f"the os.path.isfile guard did not prevent dangling symlink deletion. "
            f"(This could mean the bug has been fixed, or the test setup is wrong.)"
        )
    elif real_exists:
        print(
            f"NOT CONFIRMED — real.py was NOT deleted. "
            f"Unexpected; expected deletion of both files."
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected state: real_exists={real_exists}, "
            f"dangling_exists={dangling_exists}"
        )

except Exception as exc:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(exc).__name__}: {exc}")
    sys.exit(1)

finally:
    if tmpdir:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
[EntryPipeline] Trimmed /tmp/probe_trim_00xeou0x: kept 0 function(s), removed 0 function(s), deleted 1 source file(s).
CONFIRMED — real.py was correctly deleted, but dangling symlink 'dangling.py' was NOT deleted. spec requires deletion for all all_by_source entries when keep_by_source lacks them; os.path.isfile() returned False for the dangling symlink and the function incorrectly continued past it.
```
