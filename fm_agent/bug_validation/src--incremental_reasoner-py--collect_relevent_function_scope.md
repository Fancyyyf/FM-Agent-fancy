# Bug Report: collect_relevent_function_scope

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of paths, each relative to the extracted_functions/ directory, ordered by
    descending relevance to developer_intent; paths with equal relevance are ordered lexicographically
  - Every returned path refers to an existing regular file under extracted_functions/
  - When range is not None, the returned list has length  range
  - Returns an empty list when phases.json defines no modules, or when no module is selected
    by the relevance assessment
  - A module is selected when EITHER its natural-language description (as recorded in phases.json)
    is assessed as relevant to the developer intent, OR the module contains at least one source file
    whose path, relativized against proj_dir, matches a key in changed_functions
  - Within each selected module, a source file is included only when its content is assessed as
    relevant to the developer intent, EXCEPT that every source file present in changed_functions
    is included unconditionally
  - When the per-module file-relevance assessment cannot be obtained, every source file in that
    module is included
  - Within each included source file, the set of extracted functions whose relevance scores
    (computed from heuristic signals derived from developer_intent) rank within the top of that file
    are included
  - When per-file function ranking is unavailable for an included source file, every extracted
    function from that file is included
  - Multiple extracted-function files mapping to the same source-level function are deduplicated,
    keeping only the occurrence with the highest relevance score

---

### Actual Behavior

The function returns a list of strings. If the flattened module list from phases.json is empty, the returned list is empty. Otherwise, the list is formed by identifying the most relevant functions via a three-pass process: (1) LLM selects relevant modules based on module descriptions; (2) for each relevant module, its source files are examined to select relevant files; (3) within each relevant file, rank_functions_in_file is called to score and rank functions by relevance to developer_intent, yielding a set of function entries each with a score. All such entries are collected, sorted by descending score, and converted to relative file paths (matching the naming convention under proj_dir/fm_agent/extracted_functions/). If the parameter range is a nonnegative integer, only the first range entries are kept; if range is None, all entries are kept. The result is empty whenever the selection pipeline finds no modules, no files, or no ranked functions. Formally, let R be the return value. Then (R == []) iff (there are no modules in phases.json, or the subsequent passes produce an empty candidate set). If R  [], R is a list of strings, each an existing path relative to proj_dir/fm_agent/extracted_functions/, with no duplicates, ordered by descending relevance score, and |R| = min(range, total_candidates) when range is an integer 0, else |R| = total_candidates. All strings name extracted function files that correspond to functions defined in the selected source files of the project.

---

## Code Evidence

Line 40 and surrounding code implementing pass 1 module selection (the direct LLM call) does not select a module when it contains a file present in changed_functions, contrary to the specification.

---

## Trigger Condition

Specification requires a module to be selected when it contains a source file whose relativized path matches a key in changed_functions, even if its description is not assessed as relevant. The code only selects modules based on the LLM assessment of descriptions, ignoring the changed_functions criterion. In the counterexample, no module is selected and the function returns [], whereas the specification mandates inclusion of the module and its changed file, leading to a non-empty result.

---

## How to trigger the bug

The probe tested whether the function respects the `changed_functions` criterion in pass 1 module selection when the LLM-based description assessment returns no modules.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary project directory with `fm_agent/phases.json` containing one module (`test_module`) with `source_files: ["src/foo.py"]`, and an extracted function at `fm_agent/extracted_functions/src/foo-py/bar.py` |
| `developer_intent` | `"Add support for quantum-resistant cryptography algorithms"` (unrelated to module description) |
| `changed_functions` | `{<abs_path_to_src/foo.py>: {"added": [], "removed": [], "modified": ["bar"]}}` |
| `range` | `None` |

### Expected (spec-correct) Output

Non-empty list containing `"src/foo-py/bar.py"` — the module should be selected because it contains a source file present in `changed_functions`, regardless of the LLM's description-based assessment.

### Actual (buggy) Output

The function returned `['src/foo-py/bar.py']` — the code correctly selected the module. The `or any(...)` clause at lines 142-146 of the function correctly handles the `changed_functions` criterion.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# Create a temp project with phases.json containing one module
# with source_files: ["src/foo.py"] and a description unrelated to the intent.
# Mock _llm_select_json to return [] (no modules selected by LLM description).
# Provide changed_functions with src/foo.py.
# Call collect_relevent_function_scope().
# actual (buggy) output: ['src/foo-py/bar.py'] (non-empty, correct)
# expected (correct) output: ['src/foo-py/bar.py'] (non-empty)
```

---

## Probe Script

```python
"""Probe for collect_relevent_function_scope: verify that modules are selected when they
contain a source file present in changed_functions, even when the LLM-based module
description assessment does not select any modules.

Bug claim: pass 1 module selection ignores changed_functions when choosing modules.
The spec requires: a module is selected when EITHER its description is assessed as
relevant, OR the module contains a source file whose relativized path matches a key
in changed_functions.

Test: Mock the LLM to return [] (no modules selected by description), then provide
changed_functions with a file inside a module. If the code respects the spec, the
module should still be selected via the `or any(...)` clause.
"""
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch

# Ensure the project root is on the Python path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(os.path.dirname(_script_dir))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

error_occurred = False
error_msg = ""
result = None

tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_collect_scope_")
try:
    proj_dir = os.path.join(tmpdir, "project")
    work_dir = os.path.join(proj_dir, "fm_agent")
    extracted_dir = os.path.join(work_dir, "extracted_functions")

    # --- Step 1: Set up a minimal project with phases.json ---
    os.makedirs(work_dir, exist_ok=True)
    phases = {
        "phases": [{
            "phase": 1,
            "name": "Test Phase",
            "description": "Test phase for probe",
            "modules": [{
                "name": "test_module",
                "description": "A test module NOT relevant to developer intent",
                "source_files": ["src/foo.py"]
            }]
        }]
    }
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump(phases, f)

    # --- Step 2: Create the actual source file ---
    os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
    with open(os.path.join(proj_dir, "src", "foo.py"), "w") as f:
        f.write("def bar():\n    return 42\n")

    # --- Step 3: Create extracted function file ---
    func_dir = os.path.join(extracted_dir, "src", "foo-py")
    os.makedirs(func_dir, exist_ok=True)
    with open(os.path.join(func_dir, "bar.py"), "w") as f:
        f.write("# [SPEC]\n# Unit: src/foo-py/bar.py\n# bar() -> int\n# [SPEC]\ndef bar():\n    return 42\n")

    # --- Step 4: Prepare inputs ---
    # changed_functions maps ABSOLUTE source paths
    abs_src = os.path.abspath(os.path.join(proj_dir, "src", "foo.py"))
    changed_functions = {
        abs_src: {"added": [], "removed": [], "modified": ["bar"]}
    }
    developer_intent = "Add support for quantum-resistant cryptography algorithms"

    # --- Step 5: Call the function with mocked LLM dependencies ---
    # Mock _llm_select_json (pass 1): return [] -> no modules selected by LLM
    # The OR clause should still select the module because changed_functions has foo.py
    # Mock _opencode_select_json (pass 2): return None -> fall back to all files
    # Mock rank_functions_in_file (pass 3): return a ranked function
    with patch(
        'src.incremental_reasoner._llm_select_json',
        return_value=[]
    ):
        with patch(
            'src.incremental_reasoner._opencode_select_json',
            return_value=None
        ):
            with patch(
                'src.incremental_reasoner.rank_functions_in_file',
                return_value=[{"name": "bar", "score": 0.95, "lineno": 1, "end_lineno": 2, "file": "src/foo.py"}]
            ):
                # Also patch _parse_issue_signals to avoid parsing issues
                with patch(
                    'src.incremental_reasoner._parse_issue_signals',
                    return_value={
                        "traceback_funcs": set(),
                        "backtick_idents": set(),
                        "dotted_refs": set(),
                        "dotted_classes": set(),
                        "plain_idents": set(),
                        "exception_types": set(),
                        "all_words": ["quantum", "resistant", "cryptography"],
                    }
                ):
                    from src.incremental_reasoner import collect_relevent_function_scope
                    result = collect_relevent_function_scope(
                        proj_dir, developer_intent, changed_functions
                    )

    # --- Step 6: Evaluate ---
    # Spec says: module must be selected when it contains a file in changed_functions,
    # even if its description is not assessed as relevant.
    # If result is non-empty: the OR clause worked -> NOT CONFIRMED
    # If result is empty: the OR clause failed -> CONFIRMED

    if result and len(result) > 0:
        print(
            f"NOT CONFIRMED — result is non-empty ({len(result)} function(s)): "
            f"{result!r}"
        )
        print(
            "The function correctly selected the module via the changed_functions "
            "criterion (the 'or any(...)' clause on line 142-146), even though "
            "the LLM returned no modules by description assessment."
        )
    else:
        print(
            f"CONFIRMED — result is empty ({result!r})"
        )
        print(
            "The function returned [] despite changed_functions containing a file "
            "in the module. The module should have been selected via the "
            "'or any(...)' clause but was not."
        )

except Exception as exc:
    error_occurred = True
    error_msg = str(exc)
    print(f"ERROR: {type(exc).__name__}: {exc}")

finally:
    # Cleanup temp directory
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
NOT CONFIRMED — result is non-empty (1 function(s)): ['src/foo-py/bar.py']
The function correctly selected the module via the changed_functions criterion (the 'or any(...)' clause on line 142-146), even though the LLM returned no modules by description assessment.
```
