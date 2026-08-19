#!/usr/bin/env python3
"""Probe script: test whether _verify_single_file raises exceptions on missing sidecars."""
import sys
import os
import tempfile

# Add repo root to path so 'import src' works from the repo root
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.verification import _verify_single_file

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an extracted function file WITHOUT .spec.json / .info.json sidecars
        func_dir = os.path.join(tmpdir, "extracted_functions", "test_func-py")
        os.makedirs(func_dir, exist_ok=True)

        func_path = os.path.join(func_dir, "test_func.py")
        with open(func_path, "w") as f:
            f.write("def test_func():\n    return 42\n")

        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(output_dir, exist_ok=True)

        input_dir = os.path.join(tmpdir, "extracted_functions")

        raised = False
        exc_message = ""
        try:
            result_path, verdict = _verify_single_file(
                func_path, input_dir, output_dir, "Python"
            )
        except Exception as e:
            raised = True
            exc_message = str(e)

        if raised:
            print(f"CONFIRMED — exception raised: {exc_message}")
        else:
            expected = None  # per spec: verdict should be None when sidecars absent
            if verdict is None:
                print("NOT CONFIRMED — verdict is None (matches spec); no exception raised")
            else:
                print(
                    f"NOT CONFIRMED — _verify_single_file returned {verdict!r} "
                    f"without raising; spec expects None for missing sidecars"
                )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
