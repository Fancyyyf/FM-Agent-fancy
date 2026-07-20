import sys
import os

# Add repo root to sys.path so 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.file_utils import _has_source_code

    # Test 1: non-existent proj_dir without submodules
    proj_dir = "/tmp/fm_agent_nonexistent_dir_xyz_12345"
    actual1 = _has_source_code(proj_dir)

    # Test 2: non-existent proj_dir WITH submodules (different code path in _iter_project_source_files)
    actual2 = _has_source_code(proj_dir, submodules=["src"])

    # Test 3: existing but empty directory (should return False)
    import tempfile
    tmpdir = tempfile.mkdtemp()
    try:
        actual3 = _has_source_code(tmpdir)
    finally:
        os.rmdir(tmpdir)

    expected = False
    any_mismatch = (actual1 != expected) or (actual2 != expected) or (actual3 != expected)

except FileNotFoundError:
    print("CONFIRMED — FileNotFoundError raised instead of returning False for non-existent proj_dir")
    sys.exit(0)

except Exception as e:
    print(f"ERROR: unexpected exception: {type(e).__name__}: {e}")
    sys.exit(1)

if any_mismatch:
    print(f"CONFIRMED — actual1: {actual1!r}, actual2: {actual2!r}, actual3: {actual3!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — all calls returned expected False (actual1={actual1!r}, actual2={actual2!r}, actual3={actual3!r})")
