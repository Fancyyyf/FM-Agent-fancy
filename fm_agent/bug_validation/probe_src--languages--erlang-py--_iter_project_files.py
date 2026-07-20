"""Probe script for _iter_project_files bug: case-insensitive suffix matching is broken."""
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

from src.languages.erlang import _iter_project_files

try:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file with a known extension
        test_file = os.path.join(tmpdir, "test_module.py")
        with open(test_file, "w") as f:
            f.write("# test file")

        # Case 1: lowercase suffix → should match (control)
        results_lower = list(_iter_project_files(tmpdir, {".py"}))
        matched_lower = any("test_module.py" in p for p in results_lower)

        # Case 2: uppercase suffix → spec requires case-insensitive match,
        # but the buggy code lowercases only the extension, not the suffix set.
        results_upper = list(_iter_project_files(tmpdir, {".PY"}))
        matched_upper = any("test_module.py" in p for p in results_upper)

    # Verdict:
    # - matched_lower should be True (control)
    # - matched_upper should be True per spec (case-insensitive)
    # - matched_upper is False → bug CONFIRMED
    passed = matched_lower and not matched_upper

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(
        "CONFIRMED — lowercase suffix matched:",
        matched_lower,
        "| uppercase suffix matched:",
        matched_upper,
        "| spec requires case-insensitive match",
    )
else:
    print(
        "NOT CONFIRMED — lowercase suffix matched:",
        matched_lower,
        "| uppercase suffix matched:",
        matched_upper,
    )
