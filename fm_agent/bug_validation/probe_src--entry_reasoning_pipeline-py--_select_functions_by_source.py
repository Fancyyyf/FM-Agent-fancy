"""Probe script for bug: _select_functions_by_source returns normally when entry_func is not found instead of raising ValueError.

Spec claims: Raises ValueError when entry_func is not found among extracted functions.
Actual: Code returns normally with empty keep_by_source (buggy versions lacked the entry_func check).
"""
import sys
import os
import tempfile
import subprocess
import shutil

# This project uses a flat package layout (package=false in pyproject.toml).
# src/ modules import from 'src.xxx', so the repo root must be on the path.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _select_functions_by_source
except ImportError as e:
    print(f"ERROR: Could not import _select_functions_by_source: {e}")
    sys.exit(1)

tmpdir = tempfile.mkdtemp(dir="/tmp")
try:
    # Create a minimal Python project with a simple source file
    with open(os.path.join(tmpdir, "example.py"), "w") as f:
        f.write("def foo():\n    pass\n\ndef bar():\n    foo()\n")

    # Initialize git (required by _make_run_copy via shutil.copytree expecting a valid repo)
    subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir, capture_output=True)

    # Call with a non-existent entry_func that is NOT in the project.
    # The spec requires ValueError; the bug is that it returns normally.
    expected = "ValueError"
    passed = False
    actual = None

    try:
        result = _select_functions_by_source(
            tmpdir,
            "nonexistent::example-py::foo",  # not found in the project
            None,  # no end_funcs restriction
        )
        # Reached here means NO ValueError was raised -- bug reproduced.
        actual = f"returned normally: all_by_source has {len(result[0])} key(s), keep_by_source has {len(result[1])} key(s)"
        passed = True
    except ValueError as e:
        # Correct behavior: ValueError raised as spec requires.
        actual = f"ValueError: {e}"
        passed = False
    except Exception as e:
        actual = f"{type(e).__name__}: {e}"
        passed = True  # Wrong exception type is also a bug

except Exception as e:
    print(f"ERROR: Setup failed: {e}")
    sys.exit(1)
finally:
    # Clean up leftover .fm-entry-select directory if the function crashed mid-way
    sel_dir = tmpdir + ".fm-entry-select"
    if os.path.exists(sel_dir):
        shutil.rmtree(sel_dir, ignore_errors=True)
    shutil.rmtree(tmpdir, ignore_errors=True)

if passed:
    expected_str = str(expected)
    actual_str = repr(actual)
    print(f"CONFIRMED -- actual: {actual_str} | expected: {expected_str}")
else:
    actual_str = repr(actual)
    print(f"NOT CONFIRMED -- actual matched expected: {actual_str}")
