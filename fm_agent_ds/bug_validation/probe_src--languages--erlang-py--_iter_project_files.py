"""Probe script for bug: _iter_project_files yields symlinks despite spec forbidding it."""
import os
import sys
import tempfile

# Add the project root to sys.path so `from src.languages.erlang import ...` works
proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, proj_root)

try:
    from src.languages.erlang import _iter_project_files

    # Create a temporary directory for test fixtures
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_")

    # Create a real file with .erl extension
    real_path = os.path.join(tmpdir, "real.erl")
    with open(real_path, "w") as f:
        f.write("-module(real).\n")

    # Create a symlink to that file (also with .erl extension in the link name)
    symlink_path = os.path.join(tmpdir, "symlink.erl")
    os.symlink(real_path, symlink_path)

    # Call _iter_project_files with {".erl"} suffix set
    yielded = list(_iter_project_files(tmpdir, {".erl"}))

    # Resolve to absolute paths for comparison
    symlink_abs = os.path.abspath(symlink_path)
    real_abs = os.path.abspath(real_path)

    # The spec says symlinks should NOT be yielded.
    # If the symlink path appears in the output, the bug is confirmed.
    symlink_yielded = symlink_abs in yielded
    real_yielded = real_abs in yielded

    # Clean up temp dir
    os.unlink(symlink_path)
    os.unlink(real_path)
    os.rmdir(tmpdir)

    expected = "symlink NOT yielded (per spec)"
    actual = f"yielded paths: {yielded}"

    if symlink_yielded:
        print(f"CONFIRMED — symlink was incorrectly yielded: {symlink_abs}")
        print(f"  Real file yielded: {real_yielded}")
        print(f"  Expected: {expected}")
    else:
        print(f"NOT CONFIRMED — symlink not in output (spec-compliant). yielded: {yielded}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
