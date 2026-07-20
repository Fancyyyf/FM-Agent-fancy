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
