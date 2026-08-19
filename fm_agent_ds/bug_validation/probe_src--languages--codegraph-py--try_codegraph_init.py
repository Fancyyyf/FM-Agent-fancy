"""Probe for bug: try_codegraph_init does not remove .codegraph/ dir when codegraph.db is absent."""

import os
import sys
import tempfile
import shutil

# Probe is at fm_agent/bug_validation/probe_*.py — repo root is 3 levels up
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.languages.codegraph import try_codegraph_init

    # Create a fresh temporary workspace for all fixtures
    tmpdir = tempfile.mkdtemp(prefix="probe_codegraph_")
    proj_dir = os.path.join(tmpdir, "fake_project")
    os.makedirs(proj_dir, exist_ok=True)

    # Setup: .codegraph/ dir exists, but codegraph.db does NOT exist inside it
    codegraph_dir = os.path.join(proj_dir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    # Put a dummy file in .codegraph/ so rmtree would need to handle non-empty dirs
    dummy_file = os.path.join(codegraph_dir, "metadata.tmp")
    with open(dummy_file, "w") as f:
        f.write("partial leftovers from a failed init")

    db_path = os.path.join(codegraph_dir, "codegraph.db")
    db_exists_before = os.path.exists(db_path)
    cgdir_exists_before = os.path.isdir(codegraph_dir)

    # Call the function with force=True
    try_codegraph_init(proj_dir, force=True)

    cgdir_exists_after = os.path.isdir(codegraph_dir)
    db_exists_after = os.path.exists(db_path)

    # Spec says force=True MUST remove .codegraph/ directory.
    # The code only removes when codegraph.db exists, so we expect the dir to remain.
    # confirmed = the dir still exists (bug reproduced)
    passed = cgdir_exists_after  # True == bug reproduced

    # Cleanup temp workspace
    shutil.rmtree(tmpdir, ignore_errors=True)

    if passed:
        print(
            f"CONFIRMED — .codegraph/ dir survived force=True rebuild "
            f"(expected: removed by spec, actual: still present). "
            f"db_exists_before={db_exists_before}, cgdir_exists_before={cgdir_exists_before}, "
            f"cgdir_exists_after={cgdir_exists_after}, db_exists_after={db_exists_after}"
        )
    else:
        print(
            f"NOT CONFIRMED — .codegraph/ dir was removed as expected. "
            f"cgdir_exists_before={cgdir_exists_before}, cgdir_exists_after={cgdir_exists_after}"
        )

except Exception as e:
    # Clean up temp workspace on error
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except NameError:
        pass
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
