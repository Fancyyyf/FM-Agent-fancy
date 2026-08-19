# Bug Report: _callgraph_project_root

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns an absolute path string that identifies the original Erlang source project root. When proj_dir does not contain an 'extracted_functions' subdirectory, the absolute path of proj_dir is returned unchanged. When proj_dir contains an 'extracted_functions' subdirectory and its parent directory contains at least one file with the .erl extension, the absolute path of the parent directory is returned. Otherwise, the absolute path of proj_dir is returned.

---

### Actual Behavior

The function returns a string that is the resolved original source-project root. Let `root = os.path.abspath(proj_dir)`. The following outcomes cover normal execution (no exceptions):

1. If `os.path.isdir(os.path.join(root, "extracted_functions"))` is `False`, the function returns `root`.
2. If `os.path.isdir(os.path.join(root, "extracted_functions"))` is `True`:
   - Let `parent = os.path.dirname(root)`.
   - If `parent == root`, the function returns `root`.
   - Else, if `parent` is an existing directory and `next(_iter_project_files(parent, {".erl"}), None) is not None` (i.e., `parent` contains at least one `.erl` file belonging to the original project source tree and not excluded as pipeline workspace artifact), the function returns `parent`.
   - Else (the iterator is exhausted or `parent` contains no such `.erl` files), the function returns `root`.

Formally, with `R = os.path.abspath(proj_dir)`, `E = os.path.join(R, "extracted_functions")`, `P = os.path.dirname(R)`:
- `(not os.path.isdir(E)) ∨ (os.path.isdir(E) ∧ (P = R ∨ ¬os.path.isdir(P) ∨ next(_iter_project_files(P, {".erl"}), None) is None))` ⇒ return value is `R`.
- `os.path.isdir(E) ∧ (P ≠ R) ∧ os.path.isdir(P) ∧ (next(_iter_project_files(P, {".erl"}), None) is not None)` ⇒ return value is `P`.

Potential exceptions: If `os.path.isdir(E)` raises an `OSError` (e.g., due to inaccessible paths) the function aborts with that exception. If `os.path.isdir(E)` succeeds and we proceed to the branch that calls `_iter_project_files(P, ...)` but `P` does not exist or is not a directory, `_iter_project_files` raises a `FileNotFoundError` (or `NotADirectoryError`) because its precondition requires an existing directory. Any other I/O error during filesystem operations may also propagate as an exception.

---

## Code Evidence

Line 11: if next(_iter_project_files(parent, {".erl"}), None) is not None:

---

## Trigger Condition

The code uses _iter_project_files which skips certain directories (e.g., fm_agent) when scanning for .erl files. The specification requires returning the parent directory if it contains any .erl file, without exclusions. If all .erl files in the parent reside in excluded directories, the code returns root instead of parent, violating the specification.

---

## How to trigger the bug

When `proj_dir` is a directory that contains an `extracted_functions/` subdirectory and the parent of `proj_dir` contains `.erl` files only inside `_SKIP_DIRS`-excluded directories (such as `tests/`, `fm_agent/`), the function returns `proj_dir` instead of the parent directory. This is caused by `_iter_project_files` filtering out directories listed in `_SKIP_DIRS`, which means `.erl` files inside those excluded directories are invisible to the scan.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory path that contains an `extracted_functions/` subdirectory and whose parent contains `.erl` files only inside `_SKIP_DIRS`-excluded directories (e.g. `tests/`) |

### Expected (spec-correct) Output

The absolute path of the parent directory containing `proj_dir`.

### Actual (buggy) Output

The absolute path of `proj_dir` itself (i.e. `os.path.abspath(proj_dir)`).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
import tempfile
from src.languages.erlang import _callgraph_project_root

# Create a project dir with extracted_functions/ subdir
# and an .erl file only inside an excluded tests/ dir
tmp = tempfile.mkdtemp()
project = os.path.join(tmp, "erlang_project")
extracted = os.path.join(project, "extracted_functions")
tests = os.path.join(project, "tests")
os.makedirs(extracted)
os.makedirs(tests)
with open(os.path.join(tests, "test.erl"), "w") as f:
    f.write("-module(test).\n-export([hello/0]).\nhello() -> ok.\n")

result = _callgraph_project_root(project)
# actual (buggy) output: os.path.abspath(project) — e.g., <tmp>/erlang_project
# expected (correct) output: tmp — the parent directory
```

---

## Probe Script

```python
"""Probe for bug: _callgraph_project_root uses _SKIP_DIRS-filtered _iter_project_files
to check for .erl files, violating the spec which requires checking for ANY .erl file
in the parent directory without exclusions.
"""

import os
import sys
import tempfile

try:
    from src.languages.erlang import _callgraph_project_root
except ImportError:
    print("ERROR: Could not import _callgraph_project_root from src.languages.erlang")
    sys.exit(1)


def run_probe():
    """Create a temp directory structure where all .erl files in the parent
    reside in _SKIP_DIRS-excluded directories. The spec says the function should
    return parent; the buggy code returns root.
    """
    tmp = tempfile.mkdtemp(prefix="probe_callgraph_root_")

    # Structure:
    #   <tmp>/
    #     project/
    #       extracted_functions/   # triggers the parent-scan branch
    #       tests/                 # excluded by _SKIP_DIRS
    #         test.erl             # .erl file (only .erl in the tree)

    project_dir = os.path.join(tmp, "erlang_project")
    extracted_functions = os.path.join(project_dir, "extracted_functions")
    tests_dir = os.path.join(project_dir, "tests")

    os.makedirs(extracted_functions, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)

    # Create an .erl file inside the excluded tests/ directory
    erl_path = os.path.join(tests_dir, "test.erl")
    with open(erl_path, "w") as f:
        f.write("-module(test).\n-export([hello/0]).\nhello() -> ok.\n")

    expected = tmp  # spec says: parent directory should be returned
    try:
        actual = _callgraph_project_root(project_dir)
    except Exception as e:
        print(f"ERROR: {e}")
        # Clean up
        os.unlink(erl_path)
        for d in (tests_dir, extracted_functions, project_dir, tmp):
            try:
                os.rmdir(d)
            except OSError:
                pass
        sys.exit(1)

    projected_root = os.path.abspath(project_dir)

    # Spec: parent contains .erl → return parent (tmp)
    # Buggy code: skips tests/ dir → finds no .erl → returns root (project_dir)
    spec_correct = expected
    code_result = actual

    bug_reproduced = code_result != spec_correct

    # Clean up temp files
    try:
        os.unlink(erl_path)
        for d in (tests_dir, extracted_functions, project_dir, tmp):
            try:
                os.rmdir(d)
            except OSError:
                pass
    except OSError:
        pass

    if bug_reproduced:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(
            f"NOT CONFIRMED — actual matched expected: {actual!r}"
        )


if __name__ == "__main__":
    run_probe()
```

### Probe Output

```
CONFIRMED — actual: '/tmp/probe_callgraph_root_e2yt7cf1/erlang_project' | expected: '/tmp/probe_callgraph_root_e2yt7cf1'
```
