# Bug Report: _iter_project_files

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_iter_project_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Yields the absolute filesystem path of every regular file found recursively under
    proj_dir whose filename extension matches a member of suffixes, where the comparison
    is case-insensitive
  - Directories whose name matches a member of _SKIP_DIRS (case-insensitive) are excluded
    from traversal; no file under or within any excluded directory is ever yielded
  - Every yielded path is an absolute path, resolved by the OS according to the filesystem
    containing proj_dir
  - Each path is yielded at most once
  - Files are yielded in the order produced by a recursive depth-first directory traversal
    starting from proj_dir
  - If no regular files under proj_dir have a matching extension, the iterator yields
    nothing and terminates normally

---

### Actual Behavior

The function returns a generator object. When iterated over, the generator yields absolute filesystem paths (as strings) for all regular files found by recursively walking the directory 'proj_dir', subject to these conditions: (1) any directory whose lowercased name appears in the set `_SKIP_DIRS` is excluded from traversal (its entire subtree is skipped); (2) only files whose lowercased extension (including the leading dot) is present in the `suffixes` argument are yielded. The order of yielded paths follows the depthfirst order of `os.walk`. The generator finishes normally (implicit return) after yielding all matching files, raising `StopIteration` on subsequent next() calls. The function raises no exceptions provided the precondition holds (proj_dir exists and is accessible).

---

## Code Evidence

Line 5:             if Path(filename).suffix.lower() in suffixes:

---

## Trigger Condition

The code lowercases only the file's extension but performs an exact set membership test against the suffixes set. If any suffix in the set contains uppercase characters, it will never match the all-lowercase extension, violating the case-insensitive comparison required by the specification.

---

## How to trigger the bug

The function lowercases `Path(filename).suffix` (the file's extension) but performs an exact, case-sensitive `in` membership test against the `suffixes` set. If a caller passes a suffix set containing uppercase characters (e.g., `{".PY"}`), the all-lowercase extension will never match, even though the specification requires a case-insensitive comparison.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory containing a file named `test_module.py` |
| `suffixes` (control) | `{".py"}` — lowercase, matches correctly |
| `suffixes` (bug trigger) | `{".PY"}` — uppercase, should match per spec but does not |

### Expected (spec-correct) Output

Both `suffixes={".py"}` and `suffixes={".PY"}` should yield the absolute path to `test_module.py`.

### Actual (buggy) Output

`suffixes={".py"}` yields the file. `suffixes={".PY"}` yields nothing — the file is silently skipped.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _iter_project_files
import tempfile, os

with tempfile.TemporaryDirectory() as d:
    with open(os.path.join(d, "test_module.py"), "w") as f:
        f.write("# test")
    # lowercase suffix: works (matches)
    print(list(_iter_project_files(d, {".py"})))   # → [<path>/test_module.py]
    # uppercase suffix: BROKEN (should match per spec but doesn't)
    print(list(_iter_project_files(d, {".PY"})))   # → []  ← BUG
```

---

## Probe Script

```python
"""Probe script for _iter_project_files bug: case-insensitive suffix matching is broken."""
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.languages.erlang import _iter_project_files

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file with a known extension
        test_file = os.path.join(tmpdir, "test_module.py")
        with open(test_file, "w") as f:
            f.write("# test file")

        # Case 1: lowercase suffix → should match (control)
        results_lower = list(_iter_project_files(tmpdir, {".py"}))
        matched_lower = any("test_module.py" in p for p in results_lower)

        # Case 2: uppercase suffix → spec requires case-insensitive match,
        # but the buggy code lowercases only the extension, not the suffix set.
        results_upper = list(_iter_project_files(tmpdir, {".PY"}))
        matched_upper = any("test_module.py" in p for p in results_upper)

    # Verdict:
    # - matched_lower should be True (control)
    # - matched_upper should be True per spec (case-insensitive)
    # - matched_upper is False → bug CONFIRMED
    passed = matched_lower and not matched_upper

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(
        "CONFIRMED — lowercase suffix matched:",
        matched_lower,
        "| uppercase suffix matched:",
        matched_upper,
        "| spec requires case-insensitive match",
    )
else:
    print(
        "NOT CONFIRMED — lowercase suffix matched:",
        matched_lower,
        "| uppercase suffix matched:",
        matched_upper,
    )
```

### Probe Output

```
CONFIRMED — lowercase suffix matched: True | uppercase suffix matched: False | spec requires case-insensitive match
```
