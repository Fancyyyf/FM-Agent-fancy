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
