# Bug Report: collect_relevent_function_scope

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/incremental_reasoner-py/collect_relevent_function_scope.py`
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

Let L be the list returned by collect_relevent_function_scope. The function does not modify any of its arguments or the filesystem (it only reads files and writes logs). Under the given preconditions (proj_dir contains fm_agent/phases.json and fm_agent/extracted_functions, developer_intent is nonempty, changed_functions has the required structure, range is None or a nonnegative integer) the following holds:

If the flattened module list derived from phases.json is empty (no modules in any phase), L = [].

Otherwise, the function performs three passes:
1. Module selection: an LLM chooses a subset of modules relevant to developer_intent.
2. File selection: for each chosen module, opencode selects a subset of its source files.
3. Function selection: for each selected file, rank_functions_in_file ranks the functions and returns a list of dicts ordered by descending score. Through _extracted_files_by_method each relevant function is mapped to one or more extractedfunction file paths relative to proj_dir/fm_agent/extracted_functions. The union of these paths, ordered by the original descending scores (preserving perfile order and combining files by descending modulethenfile relevance), forms a sequence S.

If S is empty (no modules, files or functions were selected), L = [].
If range is None, L = S.
If range is a nonnegative integer, L = S[:range] (the first at most range paths).

Thus: L is a list of strings, each string is a relative path into the extracted_functions directory, and L is sorted by decreasing relevance to developer_intent. The list is empty exactly when the selection process produces no results.

---

## Code Evidence

Line 1: def collect_relevent_function_scope(proj_dir, developer_intent, changed_functions, range=None):
Line 40:     # Pass 1: module selection. The module descriptions are already parsed from phases.json

---

## Trigger Condition

Specification requires that a module is selected when it contains at least one source file whose relative path matches a key in changed_functions, even if its description is not assessed as relevant. The code performs only an LLMbased relevance assessment on module descriptions and does not incorporate the changed_functions criterion. In the counterexample, the module with an irrelevant description contains a file present in changed_functions, so it must be selected, but the code omits it, yielding an empty list instead of the required nonempty result.

---

## How to trigger the bug

The bug claim asserts that `collect_relevent_function_scope` does NOT incorporate the `changed_functions` criterion in module selection. However, inspection of the source code at `src/incremental_reasoner.py` lines 1158-1162 reveals the `relevant_modules` list comprehension explicitly includes an `or any(sf.replace("\\", "/") in changed_source_rels ...)` clause that selects modules containing files present in `changed_functions`, regardless of LLM assessment. The probe confirms this logic operates correctly.

### Inputs

| Parameter | Value |
|-----------|-------|
| selected_keys (LLM selection) | `set()` (empty — LLM selected no modules) |
| changed_source_rels | `{"src/utils/helper.py", "src/main.c"}` |
| modules[0] (core_module) | `{"name": "core_module", "source_files": ["src/core/engine.py", "src/core/alloc.py"]}` — no files in changed_source_rels |
| modules[1] (util_module) | `{"name": "util_module", "source_files": ["src/utils/helper.py", "src/utils/format.py"]}` — "src/utils/helper.py" IS in changed_source_rels |

### Expected (spec-correct) Output

`["util_module"]` — the module containing a file in `changed_functions` must be selected even though LLM found nothing relevant.

### Actual (buggy) Output

`["util_module"]` — the code DOES correctly select the module via the `changed_functions` criterion. The bug claim is not reproduced.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# The filtering expression from src/incremental_reasoner.py lines 1158-1162
selected_keys = set()
changed_source_rels = {"src/utils/helper.py"}
modules = [
    (1, {"name": "core_module", "source_files": ["src/core/engine.py"]}),
    (2, {"name": "util_module", "source_files": ["src/utils/helper.py"]}),
]
relevant = [
    (phase_num, module) for phase_num, module in modules
    if (phase_num, module.get("name")) in selected_keys
    or any(sf.replace("\\", "/") in changed_source_rels for sf in module.get("source_files", []))
]
# relevant == [(2, {"name": "util_module", ...})]
# actual (buggy) output: ["util_module"]
# expected (correct) output: ["util_module"]
# Result: NOT CONFIRMED — the code DOES incorporate the changed_functions criterion
```

---

## Probe Script

```python
"""Probe: validate whether collect_relevent_function_scope incorporates the
changed_functions criterion in module selection.

Spec claim: A module is selected when EITHER its description is assessed as
relevant by LLM, OR the module contains at least one source file whose
relativized path matches a key in changed_functions.

Bug claim: "The code performs only an LLM-based relevance assessment on module
descriptions and does not incorporate the changed_functions criterion."

This probe tests the exact filtering expression from the source code
(src/incremental_reasoner.py line ~1161) to verify the claim.
"""

import sys
import os

# --- The exact logic under test, extracted verbatim from the source ---

def _filter_relevant_modules(modules, selected_keys, changed_source_rels):
    """Verbatim reproduction of the filtering logic at lines 1158-1162 of
    src/incremental_reasoner.py."""
    return [
        (phase_num, module)
        for phase_num, module in modules
        if (phase_num, module.get("name")) in selected_keys
        or any(
            sf.replace("\\", "/") in changed_source_rels
            for sf in module.get("source_files", [])
        )
    ]


# --- Test case: LLM selects NO modules, but a module has a changed file ---

def main():
    # Simulate: LLM returned empty selection (no modules assessed as relevant)
    selected_keys = set()

    # Simulate: changed_functions maps an absolute path to a source file;
    # after relativization and normalization, it becomes "src/utils/helper.py"
    changed_source_rels = {"src/utils/helper.py", "src/main.c"}

    # Simulate: phases.json defines two modules
    modules = [
        (1, {
            "name": "core_module",
            "description": "Core infrastructure module",
            "source_files": ["src/core/engine.py", "src/core/alloc.py"],
        }),
        (2, {
            "name": "util_module",
            "description": "Utility helpers module",
            "source_files": ["src/utils/helper.py", "src/utils/format.py"],
        }),
    ]

    # Apply the filtering logic
    relevant = _filter_relevant_modules(modules, selected_keys, changed_source_rels)

    # Spec says: "util_module" must be selected because its source_file
    # "src/utils/helper.py" matches a key in changed_source_rels, even though
    # selected_keys is empty (LLM found nothing relevant).
    #
    # Bug claim says: code does NOT incorporate the changed_functions criterion,
    # so relevant would be []. But the code DOES have the `or any(...)` clause,
    # so relevant should be [(2, util_module)].

    module_names = [m.get("name") for _, m in relevant]
    expected = ["util_module"]

    if module_names == expected:
        print(
            "NOT CONFIRMED — changed_functions criterion IS incorporated: "
            f"selected modules={module_names}, expected={expected}"
        )
    elif module_names == []:
        print(
            "CONFIRMED — changed_functions criterion NOT incorporated: "
            "empty result when util_module should have been selected via "
            "changed_functions"
        )
    else:
        print(
            f"UNEXPECTED — modules selected: {module_names}, "
            f"expected: {expected}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — changed_functions criterion IS incorporated: selected modules=['util_module'], expected=['util_module']
```
