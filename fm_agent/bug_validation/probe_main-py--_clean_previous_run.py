"""Probe script for bug: main-py--_clean_previous_run.

Bug: os.path.isdir returns True for symlinks to directories, but shutil.rmtree
refuses to follow symlinks at the top level and raises OSError (Python 3.3+).
The spec requires that when work_dir refers to an existing directory, it is
permanently removed — but a symlink-to-directory triggers an exception instead.
"""
import sys
import os
import tempfile

# Add repo root to path so 'main' can be imported
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
))

# Load via the module's public entry point
from main import _clean_previous_run

actual = None
expected = None
passed = False
tmpdir = None
symlink_path = None

try:
    # Create a real target directory
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_target_")
    # Place a file inside so we can verify removal
    probe_file = os.path.join(tmpdir, "probe.txt")
    with open(probe_file, "w") as f:
        f.write("test")

    # Create a symlink pointing to the target directory
    symlink_path = tmpdir + "_link"
    os.symlink(tmpdir, symlink_path, target_is_directory=True)

    # Call the function with the symlink path.
    # Spec says: "If work_dir refers to an existing directory ... that directory
    # and all of its contents are permanently removed."
    # The symlink refers to an existing directory (os.path.isdir returns True),
    # so the spec requires removal. But shutil.rmtree raises OSError on symlinks.
    _clean_previous_run(symlink_path)

    # If we reach here, no exception was raised.
    expected = "removed"
    actual = "removed (no exception)"
    # Bug is NOT confirmed — the function handled the symlink case
    passed = False

except OSError as e:
    # shutil.rmtree raised OSError — this is the BUG.
    # The spec says the directory should be removed, but an exception was raised.
    expected = "directory removed (spec requirement)"
    actual = f"OSError: {e}"
    passed = True  # Bug CONFIRMED

except Exception as e:
    expected = "directory removed (spec requirement)"
    actual = f"Unexpected exception: {type(e).__name__}: {e}"
    passed = False

finally:
    # Cleanup: remove the symlink if it still exists
    if symlink_path and os.path.islink(symlink_path):
        try:
            os.unlink(symlink_path)
        except OSError:
            pass
    # Remove the temp target directory
    if tmpdir and os.path.isdir(tmpdir):
        import shutil
        try:
            shutil.rmtree(tmpdir)
        except OSError:
            pass

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}")
