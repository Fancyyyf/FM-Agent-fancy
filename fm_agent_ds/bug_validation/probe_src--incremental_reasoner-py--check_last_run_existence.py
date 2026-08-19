"""
Minimal probe for bug: check_last_run_existence applies submodule filter before
counting saw_function, violating the spec which separates condition (b) (unrestricted
existence of at least one non-sidecar function file) from condition (c) (submodule-
restricted readiness check).
"""
import json
import os
import sys
import tempfile
import shutil

# Import via the package entry point — run from repo root, src/ has __init__.py
sys.path.insert(0, os.path.abspath("."))
from src.incremental_reasoner import check_last_run_existence

VALID_SPEC = {
    "signature": "def foo(x: int) -> int",
    "pre_condition": "x > 0",
    "post_condition": "result > 0",
}

VALID_INFO = {
    "callees": [
        {
            "name": "bar",
            "signature": "def bar() -> int",
            "pre_condition": "",
            "post_condition": "",
        }
    ]
}


def main():
    tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    try:
        fm_agent_dir = os.path.join(tmpdir, "fm_agent")
        extracted_dir = os.path.join(fm_agent_dir, "extracted_functions")

        # Condition (a): phases.json exists
        os.makedirs(fm_agent_dir, exist_ok=True)
        with open(os.path.join(fm_agent_dir, "phases.json"), "w") as f:
            json.dump({"phases": []}, f)

        # Create a function file under extracted_functions/subdir_b/ (NOT under "subdir_a")
        func_subdir = os.path.join(extracted_dir, "subdir_b")
        os.makedirs(func_subdir, exist_ok=True)
        func_path = os.path.join(func_subdir, "my_func.py")
        with open(func_path, "w") as f:
            f.write("def my_func():\n    pass\n")

        # Valid sidecars so is_file_ready returns True
        with open(func_path + ".spec.json", "w") as f:
            json.dump(VALID_SPEC, f)
        with open(func_path + ".info.json", "w") as f:
            json.dump(VALID_INFO, f)

        # Call with submodules=["subdir_a"] — the function file is under "subdir_b",
        # NOT "subdir_a", so the code's filter skips it.
        actual = check_last_run_existence(tmpdir, submodules=["subdir_a"])

        # Spec says: return True because:
        #   (a) phases.json exists ✓
        #   (b) extracted_functions/ exists with ≥1 non-sidecar file (my_func.py) ✓
        #   (c) every file UNDER submodules is ready — there are none, so vacuous truth ✓
        # The buggy code returns False because the submodule filter is applied
        # before counting saw_function.
        expected = True
        passed = actual != expected

        if passed:
            print(
                f"CONFIRMED — actual: {actual!r} | expected: {expected!r} "
                f"(submodules=[subdir_a] but file is under subdir_b)"
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched expected: {actual!r}"
            )

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
