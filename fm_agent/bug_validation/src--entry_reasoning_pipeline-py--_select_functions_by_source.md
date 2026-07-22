# Bug Report: _select_functions_by_source

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_select_functions_by_source.py`
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

After executing the code block, exactly one of the following holds:

1. **Exception propagation path.**
   - If `_make_run_copy(proj_dir, sel_dir)` raises an exception, it propagates; `proj_dir` is not modified, `sel_dir` may not exist or be partial.
   - If `_enumerate_source_files(sel_dir)` returns an empty list, a `ValueError` is raised with a message indicating no extractable source files; `proj_dir` is not modified, `sel_dir` exists and is a copy of `proj_dir` (up to the point of enumeration).
   - If any subsequent operation (`shutil.rmtree`, `os.makedirs`, `open`/`json.dump`, `try_codegraph_init`, `run_extraction`, `_collect_phase_files`) raises an exception, it propagates; `proj_dir` is not modified, and intermediate state under `sel_dir`/`work_dir` may exist.

2. **Normal flow path.**
   - No exception is raised. `proj_dir` remains unmodified.
   - `sel_dir` (with name `proj_dir + '.fm-entry-select'`) exists and contains a full copy of `proj_dir` at the time of the call.
   - Inside `sel_dir`, the directory `fm_agent` (`work_dir`) exists and is empty of previous extractions (any prior `fm_agent/` was removed).
   - `work_dir/phases.json` contains a JSON object `{"phases": [{"phase": 0, "name": "all", "modules": [{"name": "all", "source_files": source_files}]}]}` where `source_files` is the non-empty list of extractable source file paths returned by `_enumerate_source_files(sel_dir)`.
   - If a codegraph index could be built for `sel_dir`, it has been initialized (`try_codegraph_init`); otherwise, extraction will have proceeded without it.
   - `run_extraction(sel_dir, work_dir, force=True)` has completed, writing extracted function files under `work_dir/extracted_functions/`.
   - `phase_files` is bound to the result of `_collect_phase_files(work_dir, phase)`, which is a list of `(extracted_file_relative_path, module_name)` tuples. This list may be empty.
   - Execution point is immediately after the ev...

---

## Code Evidence

Line 40: if not phase_files: (and subsequent missing return statement)

---

## Trigger Condition

The code block never returns the required tuple (all_by_source, keep_by_source); after reaching line 40 the function falls off and returns None, violating the specification.

---

## How to trigger the bug

### Verification Approach

The bug claim asserts that the `_select_functions_by_source` function "falls off and returns None" — i.e., it lacks the required `return` statement. This is a static code claim that can be verified by inspecting the source code.

### Source Code Inspection

The actual source file `src/entry_reasoning_pipeline.py` was inspected via AST analysis. Results:

- **Line 386-387**: The `if not phase_files:` guard contains `raise ValueError(f"no extractable functions found under {proj_dir!r}")`. This block does NOT fall through — it raises an exception.
- **Line 446-451**: The function ends with:
  ```python
  keep_by_source = defaultdict(set)
  for fqn in call_graph:
      keep_by_source[_entry_func_source_rel(fqn)].add(_fqn_to_ident(fqn))

  return all_by_source, keep_by_source
  ```
  There IS an explicit `return` statement returning the required `(all_by_source, keep_by_source)` tuple.

### Inputs

N/A — the bug claim is a static code property (missing return statement), verified via AST inspection.

### Expected (spec-correct) Output

`return (all_by_source, keep_by_source)` — function returns the tuple.

### Actual (buggy) Output

The claimed buggy behavior (function falls off, returns `None`) is **not present** in the source code. The function correctly returns `(all_by_source, keep_by_source)`.

### How to Reproduce

The bug cannot be reproduced — the code is correct. The `if not phase_files:` guard at line 386 raises `ValueError`, and the function returns the expected tuple at line 451.

---

## Probe Script

```py
"""Probe script for bug: _select_functions_by_source missing return statement.

Bug claim: After reaching line 40, the function falls off and returns None
instead of the required (all_by_source, keep_by_source) tuple.

Verification approach: static inspection of the function source code.
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_FILE = REPO_ROOT / "src" / "entry_reasoning_pipeline.py"


def _find_function_node(tree, func_name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    return None


def _has_explicit_return(func_node):
    for node in ast.walk(func_node):
        if isinstance(node, ast.Return) and node.value is not None:
            return True
    return False


def _find_empty_phase_files_handler(func_node):
    for node in ast.walk(func_node):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            if isinstance(test.operand, ast.Name) and test.operand.id == "phase_files":
                for stmt in node.body:
                    if isinstance(stmt, (ast.Raise, ast.Return)):
                        return True, True
                return True, False
    return False, False


def main():
    try:
        source = SOURCE_FILE.read_text()
        tree = ast.parse(source)
        func = _find_function_node(tree, "_select_functions_by_source")

        if func is None:
            print("ERROR: _select_functions_by_source not found in source")
            sys.exit(1)

        has_return = _has_explicit_return(func)
        found_guard, has_raise = _find_empty_phase_files_handler(func)
        bug_confirmed = not has_return or (found_guard and not has_raise)

        if bug_confirmed:
            print(f"CONFIRMED — has_return={has_return}, found_guard={found_guard}, has_raise={has_raise}")
        else:
            print(f"NOT CONFIRMED — has_return={has_return}, found_guard={found_guard}, has_raise={has_raise}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — has_return=True, found_guard=True, has_raise=True
```
