"""Probe for bug: _trim_project_in_place skips non-regular files (e.g. dangling
symlinks) due to os.path.isfile() guard at line 196, violating the spec which
requires unconditional deletion/modification for all paths in all_by_source.

Bug ID: src--entry_reasoning_pipeline-py--_trim_project_in_place

Expected (spec): A dangling symlink listed in all_by_source should be deleted
when keep_by_source has no entry for it.

Actual (bug): os.path.isfile() returns False for dangling symlinks, so the
function continues past without deleting or modifying the file.
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the repo root is importable so we can import from src.*
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

tmpdir = None

try:
    # ------------------------------------------------------------------
    # Step 1: Create a temporary directory with test fixtures.
    #   - real.py: a regular file with a dummy function definition
    #   - dangling.py: a dangling symlink (target doesn't exist)
    # ------------------------------------------------------------------
    tmpdir = tempfile.mkdtemp(prefix="probe_trim_")
    real_path = os.path.join(tmpdir, "real.py")
    dangling_path = os.path.join(tmpdir, "dangling.py")

    with open(real_path, "w") as f:
        f.write("def foo():\n    pass\n")

    # Create a dangling symlink — target points to a non-existent file.
    os.symlink(os.path.join(tmpdir, "nonexistent_target.py"), dangling_path)
    assert os.path.lexists(dangling_path), "symlink should exist"
    assert not os.path.isfile(dangling_path), "dangling symlink should NOT be a regular file"

    # ------------------------------------------------------------------
    # Step 2: Build the inputs that trigger the bug.
    #   all_by_source: both files are listed with function names.
    #   keep_by_source: empty — both files should be deleted per spec.
    # ------------------------------------------------------------------
    all_by_source = {
        "real.py": {"foo"},
        "dangling.py": {"bar"},
    }
    keep_by_source = {}

    # ------------------------------------------------------------------
    # Step 3: Import and call the buggy function.
    # ------------------------------------------------------------------
    from src.entry_reasoning_pipeline import _trim_project_in_place

    _trim_project_in_place(tmpdir, all_by_source, keep_by_source)

    # ------------------------------------------------------------------
    # Step 4: Check results.
    #   Spec: both files should be deleted.
    #   Bug:  real.py deleted, dangling.py still exists because
    #         os.path.isfile(dangling_path) was False → continue.
    # ------------------------------------------------------------------
    real_exists = os.path.exists(real_path)
    dangling_exists = os.path.lexists(dangling_path)

    if not real_exists and dangling_exists:
        print(
            f"CONFIRMED — real.py was correctly deleted, "
            f"but dangling symlink 'dangling.py' was NOT deleted. "
            f"spec requires deletion for all all_by_source entries "
            f"when keep_by_source lacks them; "
            f"os.path.isfile() returned False for the dangling symlink "
            f"and the function incorrectly continued past it."
        )
    elif not real_exists and not dangling_exists:
        print(
            f"NOT CONFIRMED — both files were deleted; "
            f"the os.path.isfile guard did not prevent dangling symlink deletion. "
            f"(This could mean the bug has been fixed, or the test setup is wrong.)"
        )
    elif real_exists:
        print(
            f"NOT CONFIRMED — real.py was NOT deleted. "
            f"Unexpected; expected deletion of both files."
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected state: real_exists={real_exists}, "
            f"dangling_exists={dangling_exists}"
        )

except Exception as exc:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(exc).__name__}: {exc}")
    sys.exit(1)

finally:
    if tmpdir:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
