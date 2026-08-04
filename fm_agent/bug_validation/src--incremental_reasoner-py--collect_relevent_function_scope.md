# Bug Report: collect_relevent_function_scope

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/collect_relevent_function_scope.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of relative paths (from proj_dir/fm_agent/extracted_functions/) to extracted function files, ordered by descending relevance score. Each path identifies a function judged relevant to developer_intent through three narrowing tiers: (1) modules in phases.json selected for relevance to developer_intent using the module descriptions, (2) source files within selected modules narrowed to those relevant to developer_intent, and (3) functions within selected files ranked by relevance using heuristic signal scoring with call-graph score propagation, retaining the top-ranked functions per file. Returns an empty list when phases.json contains no modules or when no modules are selected as relevant to developer_intent. When automated selection at any tier fails to produce results, the full scope at that tier is retained rather than droppedno functions are silently excluded. Source files listed in changed_functions are always included in file-level scope for their respective modules regardless of automated file selection. When range is not None, the result is truncated to the first range entries; otherwise all selected functions are returned.

---

### Actual Behavior

The function returns a list of strings. If phases.json contains no modules or the module/file selection process fails to produce any result, the returned list is empty. Otherwise, the returned list consists of paths relative to the <proj_dir>/fm_agent/extracted_functions directory, each identifying a extracted-function file. The list is ordered by descending relevance score as computed by the function-localization ranking, and if the 'range' argument was provided (a positive integer), the list is truncated to at most 'range' entries. The selection process does not modify the input arguments or their referenced objects, but may create or overwrite temporary files inside <proj_dir>/fm_agent as a side effect of calling opencode and the LLM. The result accurately reflects the three-pass scope narrowing described in the docstring: first, an LLM selects relevant modules based on module descriptions; second, opencode selects relevant source files from those modules; third, the ranking algorithm picks the most relevant functions per file. Formally: Let L denote the returned list. Then (L = []) XOR (L is a list of strings S such that each S is a valid relative path from <proj_dir>/fm_agent/extracted_functions to an existing extracted function file, and S corresponds to a function name and source file pair that was chosen as relevant; the list is sorted in descending order by a relevance score, and if range is not None, |L| = min(range, number_of_selected_functions), else |L| = number_of_selected_functions). The function raises no exceptions under the given pre-conditions.

---

## Code Evidence

Line 19-20: 'Returns an empty list when phases.json has no modules or opencode selects none / fails to produce a result.'

---

## Trigger Condition

The specification explicitly mandates that when automated selection (module, file, or function tier) fails to produce a result, the full scope at that tier is retainedno functions are silently excluded. Condition A instead returns an empty list whenever any selection process fails, which silently drops all functions and violates the 'no functions excluded' guarantee.

---

## How to trigger the bug

When the LLM call for module selection (`_llm_select_json`) fails (returns `None`), the
function treats this identically to "no modules selected" and returns an empty list.
Per the specification, all modules should instead be retained so that no functions are
silently excluded.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory with `fm_agent/phases.json` containing 2 modules |
| `developer_intent` | `"test developer intent"` |
| `changed_functions` | `[]` |
| `range` | `None` |
| `_llm_select_json` (mocked) | Returns `None` (simulates LLM failure) |

### Expected (spec-correct) Output

Non-empty list — all modules should be retained when automated module selection fails,
so the function should proceed through file selection and function ranking for all
modules rather than returning `[]`.

### Actual (buggy) Output

`[]` (empty list)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
from src.incremental_reasoner import collect_relevent_function_scope
import os, json, tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    fm_agent = os.path.join(tmpdir, "fm_agent")
    os.makedirs(fm_agent)
    with open(os.path.join(fm_agent, "phases.json"), "w") as f:
        json.dump({"phases": [{"phase": 1, "modules": [
            {"name": "m", "description": "d", "source_files": ["src/x.py"]}
        ]}]}, f)

    with patch("src.incremental_reasoner._llm_select_json", return_value=None):
        result = collect_relevent_function_scope(tmpdir, "intent", [])

    print(result)  # actual (buggy) output: []
    # expected (correct) output: non-empty list (modules retained)
```

---

## Probe Script

```python
"""Probe script for bug src--incremental_reasoner-py--collect_relevent_function_scope.

Tests that collect_relevent_function_scope silently returns [] when _llm_select_json
fails at the module selection tier, instead of retaining all modules as the spec requires.
"""
import sys
import os
import json
import tempfile
from unittest.mock import patch

# Ensure the repo root is on sys.path so package imports resolve when the
# script is run by path (e.g. `python3 fm_agent/bug_validation/probe_....py`).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.incremental_reasoner import collect_relevent_function_scope

    with tempfile.TemporaryDirectory() as tmpdir:
        fm_agent_dir = os.path.join(tmpdir, "fm_agent")
        os.makedirs(fm_agent_dir)

        phases = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [
                        {
                            "name": "module_a",
                            "description": "Module A does something",
                            "source_files": ["src/a.py"],
                        },
                        {
                            "name": "module_b",
                            "description": "Module B does other things",
                            "source_files": ["src/b.py"],
                        },
                    ],
                }
            ]
        }
        phases_path = os.path.join(fm_agent_dir, "phases.json")
        with open(phases_path, "w") as f:
            json.dump(phases, f)

        with patch("src.incremental_reasoner._llm_select_json", return_value=None):
            result = collect_relevent_function_scope(
                tmpdir, "test developer intent", changed_functions=[], range=None
            )

    # Spec (from the documentation and spec_claim): when automated selection
    # fails at any tier, the full scope at that tier is retained rather than
    # dropped -- no functions are silently excluded.  The function should fall
    # back to all modules, then proceed through the remaining passes.
    #
    # Actual (buggy) behaviour: returns [] when _llm_select_json returns None.
    expected = "non-empty list (all modules retained when LLM selection fails per spec)"
    actual = result

    # Bug confirmed if the code drops to an empty list instead of retaining scope.
    if actual == []:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as err:
    import traceback

    traceback.print_exc()
    print(f"ERROR: {err}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: [] | expected: 'non-empty list (all modules retained when LLM selection fails per spec)'
```
