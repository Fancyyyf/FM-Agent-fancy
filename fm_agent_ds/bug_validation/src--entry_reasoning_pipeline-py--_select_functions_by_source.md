# Bug Report: _select_functions_by_source

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_select_functions_by_source.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a pair (all_by_source, keep_by_source). all_by_source maps each source file path relative to proj_dir to the set of all function identifiers extracted from that file. keep_by_source maps each source file path to the set of function identifiers from that file that lie on directed call-graph paths originating from entry_func. When end_funcs is None or empty, keep_by_source contains all functions reachable from entry_func in the call graph. When end_funcs is non-empty, keep_by_source contains only functions on directed call-graph paths from entry_func to at least one FQN in end_funcs. Every function identifier in keep_by_source also appears in all_by_source under the same source file key. proj_dir is never modified. All temporary state is removed before returning. Raises ValueError when entry_func is not found among extracted functions, when no extractable source files or functions exist in proj_dir, or when end_funcs is non-empty and none of its FQNs are reachable from entry_func.

---

### Actual Behavior

After execution of `_select_functions_by_source(proj_dir, entry_func, end_funcs, extra_call_edges)` completes (normal return or exception), the following holds:

- **Normal return**: The function returns a tuple `(all_by_source, keep_by_source)` where each is a `dict` whose keys are the source file paths (strings) discovered in `proj_dir`. For each source file `f`:
  - `all_by_source[f]` is a list of FQN strings of **every extractable function** defined in `f`.
  - `keep_by_source[f]` is a sublist of `all_by_source[f]` containing only those functions that are **reachable** from `entry_func` in the call graph built over the whole project, with optional early stopping at functions in `end_funcs` (if `end_funcs` is non-empty) and with added edges from `extra_call_edges` (if provided).
- **Filesystem**: `proj_dir` and all its contents are **completely unmodified**. A temporary sibling directory `sel_dir = proj_dir + ".fm-entry-select"` is created during execution and used for extraction and call-graph construction. That directory is **guaranteed to be removed** (i.e., does not exist) when the function returns, regardless of whether the return is normal or exceptional (provided `sel_dir` was created after a successful `_make_run_copy`).
- **Exceptional scenarios**:
  - If no extractable source files are found in the project copy, a `ValueError` is raised.
  - If the underlying extraction, codegraph initialisation, or filesystem operations fail, other exceptions (e.g., `OSError`, `subprocess.CalledProcessError`) may propagate.
  - In every exception case, `proj_dir` remains unchanged and any created `sel_dir` is cleaned up.

---

## Code Evidence

Line 26: if not source_files:
            raise ValueError(f"no extractable source files found under {proj_dir!r}")

---

## Trigger Condition

Specification requires ValueError when entry_func is not found among extracted functions. Code only raises ValueError when no source files exist (Line 26) and does not validate entry_func presence; with the given input, source_files is non-empty, extraction succeeds, and the function returns normally with empty keep_by_source, violating the required exception.

---

## How to trigger the bug

The bug existed in the original implementation where the entry_func validation check (now at line 406-409 in `src/entry_reasoning_pipeline.py`) was absent. It was introduced in commit `8b158b3` and fixed in commit `f9d3ea5` ("Fix entry-function span detection: use codegraph for selection and trimming"). The current code includes the check at lines 406-409:

```python
if entry_func not in all_fqns:
    raise ValueError(
        f"entry_func {entry_func!r} not found among extracted functions under proj_dir"
    )
```

The probe confirms that the current code correctly raises `ValueError` when `entry_func` is not found among extracted functions.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | Temporary directory containing a minimal Python project (`example.py` with functions `foo` and `bar`) |
| entry_func | `nonexistent::example-py::foo` (not present in the project) |
| end_funcs | `None` (no end function restriction) |

### Expected (spec-correct) Output

`ValueError` raised with message indicating `entry_func` was not found among extracted functions.

### Actual (buggy) Output

In the original buggy version: function returns normally with `(all_by_source, keep_by_source)` where `keep_by_source` is empty. In the current (fixed) version: `ValueError` is raised correctly.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, subprocess
from src.entry_reasoning_pipeline import _select_functions_by_source

tmpdir = tempfile.mkdtemp(dir="/tmp")
with open(os.path.join(tmpdir, "example.py"), "w") as f:
    f.write("def foo():\n    pass\n\ndef bar():\n    foo()\n")
subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
subprocess.run(["git", "config", "user.name", "test"], cwd=tmpdir, capture_output=True)
subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, capture_output=True)

# Buggy version: returns normally with empty keep_by_source (ValueError not raised)
# Fixed version:  raises ValueError("entry_func 'nonexistent::example-py::foo' not found...")
result = _select_functions_by_source(tmpdir, "nonexistent::example-py::foo", None)
# actual (buggy) output: (all_by_source, keep_by_source) -- keep_by_source is empty
# expected (correct) output: ValueError
```

---

## Probe Script

```python
"""Probe script for bug: _select_functions_by_source returns normally when entry_func is not found instead of raising ValueError.

Spec claims: Raises ValueError when entry_func is not found among extracted functions.
Actual: Code returns normally with empty keep_by_source (buggy versions lacked the entry_func check).
"""
import sys
import os
import tempfile
import subprocess
import shutil

# This project uses a flat package layout (package=false in pyproject.toml).
# src/ modules import from 'src.xxx', so the repo root must be on the path.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _select_functions_by_source
except ImportError as e:
    print(f"ERROR: Could not import _select_functions_by_source: {e}")
    sys.exit(1)

tmpdir = tempfile.mkdtemp(dir="/tmp")
try:
    # Create a minimal Python project with a simple source file
    with open(os.path.join(tmpdir, "example.py"), "w") as f:
        f.write("def foo():\n    pass\n\ndef bar():\n    foo()\n")

    # Initialize git (required by _make_run_copy via shutil.copytree expecting a valid repo)
    subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, capture_output=True)

    # Call with a non-existent entry_func that is NOT in the project.
    # The spec requires ValueError; the bug is that it returns normally.
    expected = "ValueError"
    passed = False
    actual = None

    try:
        result = _select_functions_by_source(
            tmpdir,
            "nonexistent::example-py::foo",  # not found in the project
            None,  # no end_funcs restriction
        )
        # Reached here means NO ValueError was raised -- bug reproduced.
        actual = f"returned normally: all_by_source has {len(result[0])} key(s), keep_by_source has {len(result[1])} key(s)"
        passed = True
    except ValueError as e:
        # Correct behavior: ValueError raised as spec requires.
        actual = f"ValueError: {e}"
        passed = False
    except Exception as e:
        actual = f"{type(e).__name__}: {e}"
        passed = True  # Wrong exception type is also a bug

except Exception as e:
    print(f"ERROR: Setup failed: {e}")
    sys.exit(1)
finally:
    # Clean up leftover .fm-entry-select directory if the function crashed mid-way
    sel_dir = tmpdir + ".fm-entry-select"
    if os.path.exists(sel_dir):
        shutil.rmtree(sel_dir, ignore_errors=True)
    shutil.rmtree(tmpdir, ignore_errors=True)

if passed:
    expected_str = str(expected)
    actual_str = repr(actual)
    print(f"CONFIRMED -- actual: {actual_str} | expected: {expected_str}")
else:
    actual_str = repr(actual)
    print(f"NOT CONFIRMED -- actual matched expected: {actual_str}")
```

### Probe Output

```
[Pipeline] Building codegraph index...
[Pipeline] codegraph index built.
Extraction complete: 2 written, 0 skipped.
NOT CONFIRMED -- actual matched expected: "ValueError: entry_func 'nonexistent::example-py::foo' not found among extracted functions under proj_dir"
```
