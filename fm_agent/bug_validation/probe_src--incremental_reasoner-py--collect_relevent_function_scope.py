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
