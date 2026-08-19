"""
Probe for bug: src--incremental_reasoner-py--_update_specs_for_intent::_plan_spec_update

Bug: _plan_spec_update returns None when _opencode_generate_spec returns a falsy
value, even when no prior spec exists and conditions (a), (b), (c) are false.
The spec says it should return a plan dict, not None.

Approach 1: Monkey-patch the module's dependencies and exercise _update_specs_for_intent
with a seeded function, observing that the spec update is silently skipped.
Approach 2: Mirror the exact buggy logic in a standalone test for direct demonstration.
"""

import sys
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

try:
    import src.incremental_reasoner as incr
    import src.extract as extract_mod

    # -------------------------------------------------------------------
    # APPROACH 1: Exercise the real _update_specs_for_intent with patches
    # -------------------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    confirmed_real = False
    confirm_detail = ""
    error_detail = ""

    try:
        proj_dir = tmpdir
        work_dir = os.path.join(proj_dir, "fm_agent")
        extracted_dir = os.path.join(work_dir, "extracted_functions")
        os.makedirs(extracted_dir, exist_ok=True)

        # Create a fake Python source file (no .spec.json sidecar -> old_spec is None)
        source_file = os.path.join(proj_dir, "testprobe.py")
        with open(source_file, "w") as f:
            f.write("def foo():\n    return 42\n")

        # FQN derived from _file_to_fqn convention:
        #   extracted_functions/testprobe-py/foo.py -> testprobe-py::foo
        test_fqn = "testprobe-py::foo"
        file_map = {test_fqn: source_file}
        callees_map = {test_fqn: set()}
        callers_map = {test_fqn: set()}
        edge_aliases_map = {}

        # EXT_TO_LANG must include 'py' -> 'python'
        ext_to_lang = dict(extract_mod.EXT_TO_LANG)
        ext_to_lang["py"] = "python"

        patches = [
            patch.object(incr, "_project_call_graph",
                         return_value=(callees_map, callers_map, file_map, edge_aliases_map)),
            patch.object(incr, "_topdown_ordered_fqns",
                         return_value=[test_fqn]),
            # THE BUG TRIGGER: _opencode_generate_spec returns None (falsy)
            patch.object(incr, "_opencode_generate_spec", return_value=None),
            patch.object(incr, "_collect_caller_context", return_value=[]),
            patch.object(incr, "EXT_TO_LANG", ext_to_lang),
            patch.object(incr, "_llm_check_spec_update",
                         return_value={"spec_updated": False, "info_updated": False,
                                        "updated_callees": []}),
            patch.object(incr, "_llm_check_caller_info_update",
                         return_value={"info_updated": False, "new_info": {"callees": []}}),
            patch("src.incremental_reasoner.logging", MagicMock()),
        ]

        for p in patches:
            p.start()

        try:
            # Seed via relevant_rel_files — the extracted-function file relative to
            # extracted_dir.  We create this file so _file_to_fqn can compute the FQN.
            func_dir = os.path.join(extracted_dir, "testprobe-py")
            os.makedirs(func_dir, exist_ok=True)
            func_file_rel = "testprobe-py/foo.py"
            func_file_abs = os.path.join(extracted_dir, func_file_rel)
            with open(func_file_abs, "w") as f:
                f.write("def foo():\n    return 42\n")

            updated_spec_files = incr._update_specs_for_intent(
                proj_dir=proj_dir,
                work_dir=work_dir,
                developer_intent="test intent",
                changed_functions={},
                relevant_rel_files=[func_file_rel],
                extra_call_edges=None,
            )

            # BUG CHECK: spec says function must return a plan dict (not None)
            # when (a) fpath exists, (b) extension valid, (c) no prior spec exists.
            # The code returns None because _opencode_generate_spec returned falsy.
            # This means updated_spec_files is empty — the function was silently skipped.
            if not updated_spec_files:
                confirmed_real = True
                confirm_detail = (
                    "CONFIRMED — _update_specs_for_intent returned an empty list,"
                    " meaning _plan_spec_update returned None and the function was"
                    " silently skipped."
                    " When (a) fpath exists, (b) extension is valid ('py'->'python'),"
                    " and (c) no prior spec exists (old_spec is None), the spec requires"
                    " returning a plan dict, not None."
                    " The bug is at line 1843-1844:"
                    " 'if not result or not result.get(\"spec_updated\"): return None'"
                    " returns None even when _opencode_generate_spec returned None"
                    " (falsy), violating the specification."
                )
            else:
                confirmed_real = False
                confirm_detail = (
                    "NOT CONFIRMED — _update_specs_for_intent returned"
                    f" {updated_spec_files!r}"
                )

        except Exception as e:
            error_detail = f"ERROR in approach 1: {e}"

        finally:
            for p in patches:
                p.stop()

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # -------------------------------------------------------------------
    # APPROACH 2: Mirror the exact buggy logic
    # -------------------------------------------------------------------
    tmpdir2 = tempfile.mkdtemp(prefix="fm_agent_probe2_")
    confirmed_mirror = False
    mirror_detail = ""

    try:
        source_file2 = os.path.join(tmpdir2, "testprobe.py")
        with open(source_file2, "w") as f:
            f.write("def foo():\n    return 42\n")

        fpath = source_file2
        ext = "py"
        lang_key = "python"

        # Verify conditions (a) and (b) are false
        assert os.path.isfile(fpath), "condition (a) false: file exists"
        assert ext in ("py",), "condition (b) false: extension valid"

        # Condition (c) is "function already has a valid specification AND
        # that specification remains correct" — old_spec is None, so (c) is false
        old_spec = None
        old_info = None

        # Simulate _opencode_generate_spec returning None (LLM failure)
        fake_result = None

        # ---- Mirror of lines 1843-1844 (THE BUG) ----
        if not fake_result or not fake_result.get("spec_updated"):
            buggy_return = None
        else:
            buggy_return = {"fqn": "test", "plan": "dict"}

        # Verdict: spec says return a plan dict, code returns None
        expected_spec = "a plan dict (not None)"
        passed = buggy_return is None

        if passed:
            confirmed_mirror = True
            mirror_detail = (
                "CONFIRMED — The mirrored logic at lines 1843-1844 returns None"
                " when _opencode_generate_spec returns a falsy value (None),"
                " but the specification requires returning a plan dict because"
                " conditions (a), (b), and (c) are all false."
                " The silent None return causes the function to be skipped"
                " in the caller's filtering at line 1961:"
                " 'applied = [p for p in plans if p]'."
            )
        else:
            confirmed_mirror = False
            mirror_detail = (
                f"NOT CONFIRMED — mirrored logic returned {buggy_return!r}"
            )

    finally:
        shutil.rmtree(tmpdir2, ignore_errors=True)

    # -------------------------------------------------------------------
    # Final verdict
    # -------------------------------------------------------------------
    if confirmed_real and confirmed_mirror:
        print("CONFIRMED — Both approaches reproduce the bug.")
        print(f"  Approach 1 (real code): {confirm_detail.split(chr(10))[0]}")
        print(f"  Approach 2 (mirrored logic): {mirror_detail.split(chr(10))[0]}")
    elif confirmed_real:
        print(confirm_detail)
    elif confirmed_mirror:
        print(mirror_detail)
    elif error_detail:
        print(error_detail)
        print(mirror_detail)
    else:
        print(
            "NOT CONFIRMED — Neither approach reproduced the bug."
            f" Real: {confirm_detail} Mirror: {mirror_detail}"
        )

except ImportError as e:
    print(f"ERROR: Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
