# Bug Report: _callgraph_project_root

**Source file:** `src/languages/erlang-py/_callgraph_project_root.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the absolute, normalized path to the original source-project root directory
  - If proj_dir does not contain an "extracted_functions" subdirectory, returns abspath(proj_dir)
  - If proj_dir is the filesystem root (parent directory resolves to itself), returns abspath(proj_dir)
  - If proj_dir contains "extracted_functions" and is not the filesystem root, and the parent directory contains at least one Erlang source file (.erl extension), returns the parent directory of proj_dir
  - If proj_dir contains "extracted_functions" and is not the filesystem root, but the parent directory contains no Erlang source files, returns abspath(proj_dir)

---

### Actual Behavior

Let `R = os.path.abspath(proj_dir)`. Let `HAS_EF = os.path.isdir(os.path.join(R, 'extracted_functions'))`. Let `P = os.path.dirname(R)`. Let `HAS_ERL = (next(_iter_project_files(P, {'.erl'}), None) is not None)`, where `_iter_project_files` yields absolute paths of files under `P` (recursively) with extension `.erl`, ignoring directories whose name appears in the global set `_SKIP_DIRS`. The function returns a string `result` such that: if `not HAS_EF` then `result == R`; else (`HAS_EF` is true), if `P == R` then `result == R`, else if `HAS_ERL` then `result == P`, else `result == R`. In all cases, `result` is the absolute path of either `proj_dir` or its immediate parent directory. The function does not modify the filesystem, raise exceptions under the given pre-condition, or have any other observable effect.

---

## Code Evidence

Line 11: if next(_iter_project_files(parent, {".erl"}), None) is not None:

---

## Trigger Condition

The specification requires returning the parent directory whenever it contains at least one Erlang source file, but the codes reliance on _iter_project_files ignores files inside directories whose names appear in _SKIP_DIRS. In the counterexample, the only .erl file resides in a skipped directory, causing the code to incorrectly return the original proj_dir instead of the parent, thereby violating the specification.

---

## How to trigger the bug

The bug manifests when an FM-Agent workspace (`proj_dir` contains an `extracted_functions/` subdirectory) is located inside a parent project directory whose only `.erl` files reside in directories whose names are in `_SKIP_DIRS` (e.g., `test/`, `tests/`, `_build/`, `deps/`, `.git/`, `.venv/`, `.codegraph/`, `fm_agent/`). The `_iter_project_files` helper skips these directories entirely, so `_callgraph_project_root` incorrectly concludes that the parent has no `.erl` files and falls back to returning `proj_dir`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A directory path containing an `extracted_functions/` subdirectory, whose parent directory has `.erl` files ONLY inside `_SKIP_DIRS` directories (e.g., `test/dummy.erl`) |

### Expected (spec-correct) Output

The absolute path to the **parent** directory of `proj_dir` (e.g., `/tmp/bug_probe_xxx/parent`)

### Actual (buggy) Output

The absolute path to `proj_dir` itself (e.g., `/tmp/bug_probe_xxx/parent/workspace`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Create a directory structure where a project has `.erl` files only in `test/` (or another `_SKIP_DIRS` entry), with an FM-Agent workspace inside it:

```python
import os, sys
sys.path.insert(0, '.')
from src.languages.erlang import _callgraph_project_root

# Setup: parent has test/dummy.erl (test is in _SKIP_DIRS)
# workspace has extracted_functions/ (marks it as FM-Agent workspace)
parent_dir = "..."
workspace_dir = os.path.join(parent_dir, "workspace")
os.makedirs(os.path.join(workspace_dir, "extracted_functions"))
os.makedirs(os.path.join(parent_dir, "test"))
with open(os.path.join(parent_dir, "test", "dummy.erl"), "w") as f:
    f.write("-module(dummy).\n")

result = _callgraph_project_root(workspace_dir)
# actual (buggy) output: workspace_dir (should be parent_dir)
# expected (correct) output: parent_dir
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

# Add the snapshot root to the Python path so we can import from src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.languages.erlang import _callgraph_project_root

bug_id = "src--languages--erlang-py--_callgraph_project_root"
probe_output = None

# Build a temporary directory structure that triggers the bug:
#   parent/
#     test/           <-- directory name in _SKIP_DIRS
#       dummy.erl     <-- only .erl file, hidden by _iter_project_files
#     workspace/
#       extracted_functions/   <-- marks this as an FM-Agent workspace
#
# proj_dir = parent/workspace
#   -> spec:  parent contains .erl, return parent
#   -> bug:   _iter_project_files skips test/, so .erl is invisible, return workspace

tmp_root = tempfile.mkdtemp(prefix="bug_probe_")

try:
    # parent directory
    parent_dir = os.path.join(tmp_root, "parent")

    # workspace with extracted_functions subdirectory
    workspace_dir = os.path.join(parent_dir, "workspace")
    extracted_func_dir = os.path.join(workspace_dir, "extracted_functions")
    os.makedirs(extracted_func_dir)

    # test/ directory (name is in _SKIP_DIRS) with a .erl file inside
    test_dir = os.path.join(parent_dir, "test")
    os.makedirs(test_dir)
    erl_file = os.path.join(test_dir, "dummy.erl")
    with open(erl_file, "w") as f:
        f.write("-module(dummy).\n-export([hello/0]).\nhello() -> ok.\n")

    # Call _callgraph_project_root with workspace_dir as proj_dir
    actual = _callgraph_project_root(workspace_dir)
    actual = os.path.realpath(actual)

    # Spec says: parent has .erl → return parent
    expected = os.path.realpath(parent_dir)

    passed = actual != expected  # True → bug reproduced (actual != expected)

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        print(f"  Trigger: .erl file at {erl_file!r} inside _SKIP_DIRS directory 'test'")
        print(f"  was not found by _iter_project_files, so _callgraph_project_root")
        print(f"  returned proj_dir instead of parent.")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    shutil.rmtree(tmp_root, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual: '/tmp/bug_probe_p0y79qdo/parent/workspace' | expected: '/tmp/bug_probe_p0y79qdo/parent'
  Trigger: .erl file at '/tmp/bug_probe_p0y79qdo/parent/test/dummy.erl' inside _SKIP_DIRS directory 'test'
  was not found by _iter_project_files, so _callgraph_project_root
  returned proj_dir instead of parent.
```
