# Bug Report: _select_functions_by_source

**Source file:** `/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_select_functions_by_source.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- proj_dir is never mutated; all mutations occur in a temporary sibling directory
    that is destroyed before this function returns
  - Returns a tuple (all_by_source, keep_by_source) where:
    - all_by_source is a dict mapping each source-file relative path to the set of
      ALL function names that were extractable from that source file
    - keep_by_source is a dict mapping each source-file relative path to the set of
      function names that are transitively reachable from entry_func in the static
      call graph; when end_funcs is non-empty, this set is further restricted to
      function names that lie on at least one call-chain path from entry_func to
      some member of end_funcs
  - Raises ValueError when:
    - No extractable source files are found under proj_dir
    - No extractable functions are found under proj_dir
    - entry_func is not among the extracted functions
    - end_funcs is non-empty and no member of end_funcs is reachable from entry_func
      in the call graph
  - When extra_call_edges is provided, its supplemental edges contribute to the call
    graph used for reachability analysis

---

### Actual Behavior

After normal execution, the function returns a tuple (all_by_source, keep_by_source). all_by_source maps each relative source file path (as enumerated from a temporary copy of proj_dir) to a list of fully qualified names of all extractable functions in that file. keep_by_source maps each source file path to a list of fully qualified names of functions that are reachable from entry_func in the call graph; if end_funcs is non-empty, only those functions that lie on at least one call chain from entry_func to a function in end_funcs are included. The call graph is built using a full extraction of a temporary copy of proj_dir, incorporating any extra_call_edges if provided. The temporary copy and all extraction artifacts are completely removed before the function returns; proj_dir remains unmodified and no side effects persist. If the temporary copy contains no extractable source files, a ValueError is raised. In that case, proj_dir is unmodified, but the temporary copy (proj_dir + '.fm-entry-select') may remain on disk.

---

## Code Evidence

Line 1: def _select_functions_by_source(...) does not implement the required ValueError checks for entry_func not found or end_funcs unreachable; only the absence of source files is checked (Line 25-26).

---

## Trigger Condition

The specification requires raising ValueError when entry_func is not among the extracted functions, when end_funcs is non-empty but no member is reachable, and when no extractable functions exist. The code's described behavior (Condition A) only raises ValueError for missing source files, leaving these conditions unhandled. A direct counterexample is an input with existing source files but an entry_func name that does not match any extracted function  the code will not raise ValueError, violating the spec.

---

## How to trigger the bug

The logic verification incorrectly claims that `_select_functions_by_source` does not check for `entry_func` not being among extracted functions. In reality, the source code at `src/entry_reasoning_pipeline.py` lines 372-375 implements exactly this check:

```python
if entry_func not in all_fqns:
    raise ValueError(
        f"entry_func {entry_func!r} not found among extracted functions under proj_dir"
    )
```

The probe confirms that this code path is exercised and the `ValueError` is correctly raised.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | A temp directory containing `hello.py` with `def hello(): ...` |
| entry_func | `nonexistent_module::nonexistent_func` |
| end_funcs | `[]` (empty) |
| extra_call_edges | `None` (default) |

### Expected (spec-correct) Output

`ValueError` raised with message containing "entry_func" and "not found"

### Actual (buggy) Output

`ValueError` raised: `entry_func 'nonexistent_module::nonexistent_func' not found among extracted functions under proj_dir`

The actual behavior matches the specification. The bug is NOT reproducible — the code correctly handles this case.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, tempfile, shutil
sys.path.insert(0, ".")
from src.entry_reasoning_pipeline import _select_functions_by_source

tmp_dir = tempfile.mkdtemp(prefix="bug_probe_")
with open(os.path.join(tmp_dir, "hello.py"), "w") as f:
    f.write("def hello():\n    return 'world'\n")

try:
    _select_functions_by_source(tmp_dir, "nonexistent_module::nonexistent_func", [])
    print("NOT CONFIRMED — no ValueError raised")
except ValueError as e:
    print(f"NOT CONFIRMED — ValueError raised as spec requires: {e}")
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)

# Output: NOT CONFIRMED — ValueError raised as spec requires: entry_func 'nonexistent_module::nonexistent_func' not found among extracted functions under proj_dir
```

---

## Probe Script

```python
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/tmp/fm_agent_wt_FM-Agent_9w930mtx/snapshot")

try:
    from src.entry_reasoning_pipeline import _select_functions_by_source

    tmp_dir = tempfile.mkdtemp(prefix="bug_probe_")
    src_file = os.path.join(tmp_dir, "hello.py")
    with open(src_file, "w") as f:
        f.write("def hello():\n    return 'world'\n")

    try:
        _select_functions_by_source(
            tmp_dir,
            "nonexistent_module::nonexistent_func",
            end_funcs=[],
        )
        print("NOT CONFIRMED — no ValueError raised for missing entry_func; the check is not present")
    except ValueError as e:
        msg = str(e)
        if "entry_func" in msg and "not found" in msg:
            print(f"NOT CONFIRMED — ValueError was raised for missing entry_func, as the spec requires: {msg}")
        else:
            print(f"CONFIRMED — unexpected ValueError raised (not the entry_func check): {msg}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
except Exception as e:
    print(f"ERROR during import/setup: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
[Pipeline] Building codegraph index...
[Pipeline] codegraph index built.
Extraction complete: 1 written, 0 skipped.
NOT CONFIRMED — ValueError was raised for missing entry_func, as the spec requires: entry_func 'nonexistent_module::nonexistent_func' not found among extracted functions under proj_dir
```
