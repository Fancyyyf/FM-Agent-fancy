# Bug Report: _has_source_code

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/src/file_utils-py/_has_source_code.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when proj_dir (optionally scoped to submodules) contains at least one
    file whose extension matches a pipeline-supported programming language.
  - Returns False when no such file exists within the applicable scope, including when
    proj_dir does not exist, is empty, contains no recognized source files, or when
    submodules narrows the scope to a subset of the tree that contains no recognized
    source files.
  - When submodules is None, the search covers the entire directory tree under proj_dir,
    excluding directories whose names begin with "." and well-known build/package
    directories.
  - When submodules is provided and non-empty, only files whose project-relative path
    begins with one of the listed subdirectory names are considered.

---

### Actual Behavior

The function returns True if and only if the underlying iterator `_iter_project_source_files(proj_dir, submodules)` produces at least one path (i.e., a file with a pipeline-supported extension exists in the directory tree rooted at `proj_dir`, optionally confined to the submodules listed in `submodules`, excluding hidden directories and build/package directories). Otherwise it returns False. The call has no side effects. Formally: let S = { p | p is yielded by `_iter_project_source_files(proj_dir, submodules)` } ; then `_has_source_code(proj_dir, submodules)` = True  S  .

---

## Code Evidence

Line 3: for _ in _iter_project_source_files(proj_dir, submodules):

---

## Trigger Condition

The specification requires that _has_source_code return False when proj_dir does not exist. However, the code does not validate that proj_dir is a directory before calling _iter_project_source_files. If proj_dir does not exist, the iterator may raise a FileNotFoundError, which propagates uncaught, causing the function to raise an exception instead of returning False as required.

---

## How to trigger the bug

The bug could not be reproduced. In Python 3.12 (the runtime used), `os.walk()` silently handles non-existent directories by yielding nothing, so `_iter_project_source_files` produces an empty iterator, the `for` loop body never executes, and `_has_source_code` correctly returns `False`. The `FileNotFoundError` described in the trigger condition does not occur in this Python version.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | `"/tmp/fm_agent_nonexistent_dir_xyz_12345"` |
| `submodules` | `None` (Test 1), `["src"]` (Test 2) |

### Expected (spec-correct) Output

`False`

### Actual (buggy) Output

`False`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import _has_source_code

# Test with non-existent directory
result1 = _has_source_code("/tmp/fm_agent_nonexistent_dir_xyz_12345")
# actual (buggy) output: False
# expected (correct) output: False

# Test with non-existent directory + submodules
result2 = _has_source_code("/tmp/fm_agent_nonexistent_dir_xyz_12345", submodules=["src"])
# actual (buggy) output: False
# expected (correct) output: False
```

---

## Probe Script

```python
import sys
import os

# Add repo root to sys.path so 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.file_utils import _has_source_code

    # Test 1: non-existent proj_dir without submodules
    proj_dir = "/tmp/fm_agent_nonexistent_dir_xyz_12345"
    actual1 = _has_source_code(proj_dir)

    # Test 2: non-existent proj_dir WITH submodules (different code path in _iter_project_source_files)
    actual2 = _has_source_code(proj_dir, submodules=["src"])

    # Test 3: existing but empty directory (should return False)
    import tempfile
    tmpdir = tempfile.mkdtemp()
    try:
        actual3 = _has_source_code(tmpdir)
    finally:
        os.rmdir(tmpdir)

    expected = False
    any_mismatch = (actual1 != expected) or (actual2 != expected) or (actual3 != expected)

except FileNotFoundError:
    print("CONFIRMED — FileNotFoundError raised instead of returning False for non-existent proj_dir")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
    sys.exit(1)

if any_mismatch:
    print(f"CONFIRMED — actual1: {actual1!r}, actual2: {actual2!r}, actual3: {actual3!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — all calls returned expected False (actual1={actual1!r}, actual2={actual2!r}, actual3={actual3!r})")
```

### Probe Output

```
NOT CONFIRMED — all calls returned expected False (actual1=False, actual2=False, actual3=False)
```
