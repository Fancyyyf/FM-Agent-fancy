"""Probe for _remove_stale_extracted: verify all removed functions' files are deleted, even
when multiple removed functions belong to the same source file.

Bug claim: _modified_function_targets returns only one path per source file, so with two
removed functions in the same source file, only the first function's extracted file is deleted.
"""
import sys
import os
import tempfile
import shutil

# Ensure the project root is on the Python path for import
_script_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.dirname(os.path.dirname(_script_dir))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

error_occurred = False
error_msg = ""

try:
    from src.incremental_reasoner import _remove_stale_extracted
except ImportError as e:
    print(f"ERROR: Could not import _remove_stale_extracted: {e}")
    print("NOT CONFIRMED — import failed")
    sys.exit(1)

# Set up temporary directory structure simulating a project with:
# - proj_dir = <tmp>/project
# - Two extracted function files for the same source file (src/foo.py):
#     fm_agent/extracted_functions/src/foo-py/func1.py
#     fm_agent/extracted_functions/src/foo-py/func2.py
# - Both functions are reported as "removed" in modified_functions
tmpdir = tempfile.mkdtemp(prefix="fm_agent_probe_")
try:
    proj_dir = os.path.join(tmpdir, "project")
    extracted_base = os.path.join(proj_dir, "fm_agent", "extracted_functions")

    # Source file path (absolute)
    abs_src = os.path.join(proj_dir, "src", "foo.py")

    # Extracted function directory for src/foo.py -> src/foo-py/
    func_dir = os.path.join(extracted_base, "src", "foo-py")
    os.makedirs(func_dir, exist_ok=True)

    # Create two extracted function files for two "removed" functions
    func1_path = os.path.join(func_dir, "func1.py")
    func2_path = os.path.join(func_dir, "func2.py")

    with open(func1_path, "w") as f:
        f.write("# [SPEC]\n# extracted function func1\n")
    with open(func2_path, "w") as f:
        f.write("# [SPEC]\n# extracted function func2\n")

    # Verify files exist before calling the function
    assert os.path.isfile(func1_path), "func1.py should exist before test"
    assert os.path.isfile(func2_path), "func2.py should exist before test"

    # Build modified_functions with BOTH functions as "removed"
    modified_functions = {
        abs_src: {
            "removed": ["func1", "func2"],
            "added": [],
            "modified": [],
        }
    }

    # Call the function under test
    _remove_stale_extracted(proj_dir, modified_functions)

    # Check results
    func1_exists = os.path.isfile(func1_path)
    func2_exists = os.path.isfile(func2_path)
    func_dir_exists = os.path.isdir(func_dir)

    # The spec says: every removed function's extracted file should be deleted.
    # The bug claim says: only the first removed function per source file gets deleted.
    #
    # If both files are gone -> NOT CONFIRMED (the code is correct, bug doesn't exist)
    # If only func1 is gone but func2 still exists -> CONFIRMED (bug reproduced)
    # If neither is gone -> NOT CONFIRMED (unexpected behavior but not the claimed bug)
    # If both are gone but dir still exists -> NOT CONFIRMED (files deleted, dir cleanup
    #   is a separate concern not relevant to this bug report)

    both_deleted = not func1_exists and not func2_exists
    only_first_deleted = not func1_exists and func2_exists
    neither_deleted = func1_exists and func2_exists

    if only_first_deleted:
        print(
            f"CONFIRMED — func1.py deleted ({func1_path} exists={func1_exists}), "
            f"but func2.py NOT deleted ({func2_path} exists={func2_exists}). "
            f"Only the first removed function per source file was handled."
        )
    elif both_deleted:
        if func_dir_exists:
            print(
                f"NOT CONFIRMED — both func1.py ({func1_path} exists={func1_exists}) "
                f"and func2.py ({func2_path} exists={func2_exists}) were deleted. "
                f"Directory {func_dir} still exists (not empty due to retained files, "
                f"or not yet pruned), but the core bug claim (only first function deleted) "
                f"is false — the code correctly removes all removed functions."
            )
        else:
            print(
                f"NOT CONFIRMED — both func1.py and func2.py were deleted, "
                f"AND the empty directory was pruned. "
                f"The code correctly handles multiple removed functions per source file."
            )
    elif neither_deleted:
        print(
            f"NOT CONFIRMED — neither func1.py (exists={func1_exists}) "
            f"nor func2.py (exists={func2_exists}) was deleted. "
            f"Unexpected: the function didn't delete any files, but this doesn't match "
            f"the claimed bug pattern (only-first-function-deleted)."
        )
    else:
        # func2 was deleted but func1 wasn't — weird but not the claimed bug
        print(
            f"NOT CONFIRMED — unexpected: func1.py exists={func1_exists}, "
            f"func2.py exists={func2_exists}. "
            f"This doesn't match the claimed bug pattern."
        )

except Exception as exc:
    error_occurred = True
    error_msg = str(exc)
    print(f"ERROR: {exc}")

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
