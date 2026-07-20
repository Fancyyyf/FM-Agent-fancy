import sys
import os
import tempfile
import shutil

# Ensure the project root is on sys.path so the src package resolves.
# The script is meant to be run from repo root, so os.getcwd() is the repo root.
sys.path.insert(0, os.getcwd())

try:
    from src.generate_topdown_layers import _collect_phase_files

    proj_dir = tempfile.mkdtemp()

    # The spec says: replace last "." with "-" unconditionally.
    # For ".hiddenfile", rfind('.') returns 0.
    # The bug (last_dot > 0 guard) skips replacement → dir_name stays ".hiddenfile"
    # Correct behavior: dir_name should be "-hiddenfile"

    # Create ONLY the spec-correct directory: extracted_functions/-hiddenfile
    correct_dir = os.path.join(proj_dir, "extracted_functions", "-hiddenfile")
    os.makedirs(correct_dir)
    with open(os.path.join(correct_dir, "some_func.py"), "w") as f:
        f.write("# extracted function content\n")

    phase_data = {
        "modules": [
            {
                "name": "test_module",
                "source_files": [".hiddenfile"]
            }
        ]
    }

    actual = _collect_phase_files(proj_dir, phase_data)

    # Expected (spec-correct): files from extracted_functions/-hiddenfile/ should be collected
    # Actual (buggy):     looks in extracted_functions/.hiddenfile/ instead → finds nothing
    expected_count = 1  # one file in -hiddenfile/
    actual_count = len(actual)

    passed = actual_count != expected_count  # True → bug reproduced (returned empty)

    if passed:
        print(f'CONFIRMED — actual count: {actual_count} | expected count: {expected_count}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual_count} file(s)')

    shutil.rmtree(proj_dir)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
