"""Probe: UnicodeDecodeError in _collect_changed_functions::_git via text=True.

The nested helper _git() uses subprocess.run(..., text=True) without error
handling for binary stdout. This probe creates a temp git repo with a binary
.py file and calls _collect_changed_functions to exercise _git("show", ...)
which will try to decode binary blob content as text.

IMPORTANT: All work happens in a temporary directory outside fm_agent/.
The only output is the CONFIRMED/NOT CONFIRMED line on stdout.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import traceback


def main():
    # script is at repo_root/fm_agent/bug_validation/probe_xxx.py
    # Walk up: probe → bug_validation → fm_agent → repo_root (3 levels)
    repo_root = os.path.abspath(__file__)
    for _ in range(3):
        repo_root = os.path.dirname(repo_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    work_dir = tempfile.mkdtemp(prefix="bug_probe_")
    got_confirmed = False
    last_error = None

    try:
        # ── Setup: a git repo with a binary .py file ──
        proj_dir = os.path.join(work_dir, "test_repo")
        os.makedirs(proj_dir)

        _run(["git", "-C", proj_dir, "init", "--quiet"])
        _run(["git", "-C", proj_dir, "config", "user.email", "test@test.com"])
        _run(["git", "-C", proj_dir, "config", "user.name", "Test"])

        # Create a binary file with a .py extension.
        # Bytes 0x80-0xFF: every single byte is an invalid UTF-8 start byte,
        # so text=True decoding WILL fail regardless of locale.
        binary_file = os.path.join(proj_dir, "crash.py")
        with open(binary_file, "wb") as f:
            f.write(b'\x80\x81\x82\x83\xff\xfe\xfd\xfc\nprint("this is not valid Python")')

        _run(["git", "-C", proj_dir, "add", "crash.py"])
        _run(["git", "-C", proj_dir, "commit", "-m", "initial commit", "--quiet"])

        # Modify the file (unstaged change) so diff picks it up.
        with open(binary_file, "wb") as f:
            f.write(b'\x80\x81\x82\x83\xff\xfe\xfd\xfc\x00\nprint("modified")')

        # ── Exercise the buggy code path ──
        from src.incremental_reasoner import _collect_changed_functions

        try:
            _collect_changed_functions(proj_dir, "HEAD")
            # If we get here, no UnicodeDecodeError was raised.
            # Either the code path didn't exercise _git("show", ...) (e.g. CodeGraph
            # was used) or the file content happened to decode without error.
        except UnicodeDecodeError as exc:
            got_confirmed = True
            print(f"CONFIRMED - UnicodeDecodeError: {exc}")
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"NOT CONFIRMED - unexpected error: {last_error}")
            # Print traceback for debugging but do NOT exit with error code,
            # the keyword NOT CONFIRMED on stdout is what matters.
            traceback.print_exc()
            return

        # ── Attempt 2: try a more explicitly invalid UTF-8 sequence ──
        proj_dir2 = os.path.join(work_dir, "test_repo2")
        os.makedirs(proj_dir2)
        _run(["git", "-C", proj_dir2, "init", "--quiet"])
        _run(["git", "-C", proj_dir2, "config", "user.email", "test@test.com"])
        _run(["git", "-C", proj_dir2, "config", "user.name", "Test"])

        binary_file2 = os.path.join(proj_dir2, "crash2.py")
        # BOM-like marker followed by bytes that will form an invalid sequence
        with open(binary_file2, "wb") as f:
            f.write(b'\xff\xfe\x00\x00\xde\xad\xbe\xef')
        _run(["git", "-C", proj_dir2, "add", "crash2.py"])
        _run(["git", "-C", proj_dir2, "commit", "-m", "initial", "--quiet"])

        # Modify
        with open(binary_file2, "wb") as f:
            f.write(b'\xff\xfe\x00\x00\xde\xad\xbe\xef\x00')

        try:
            _collect_changed_functions(proj_dir2, "HEAD")
        except UnicodeDecodeError as exc:
            got_confirmed = True
            print(f"CONFIRMED - UnicodeDecodeError (attempt 2): {exc}")
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"NOT CONFIRMED - unexpected error (attempt 2): {last_error}")
            traceback.print_exc()
            return

        # ── Attempt 3: test the vulnerable pattern directly ──
        # Since _git is a nested closure, we test the identical pattern:
        # subprocess.run(..., text=True) with binary git output.
        proj_dir3 = os.path.join(work_dir, "test_repo3")
        os.makedirs(proj_dir3)
        _run(["git", "-C", proj_dir3, "init", "--quiet"])
        _run(["git", "-C", proj_dir3, "config", "user.email", "test@test.com"])
        _run(["git", "-C", proj_dir3, "config", "user.name", "Test"])

        binary_file3 = os.path.join(proj_dir3, "crash3.py")
        with open(binary_file3, "wb") as f:
            f.write(bytes(range(256)))
        _run(["git", "-C", proj_dir3, "add", "crash3.py"])
        _run(["git", "-C", proj_dir3, "commit", "-m", "initial", "--quiet"])

        with open(binary_file3, "wb") as f:
            f.write(bytes(range(256)) + b'\x00')

        try:
            _collect_changed_functions(proj_dir3, "HEAD")
        except UnicodeDecodeError as exc:
            got_confirmed = True
            print(f"CONFIRMED - UnicodeDecodeError (attempt 3): {exc}")
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"NOT CONFIRMED - unexpected error (attempt 3): {last_error}")
            traceback.print_exc()
            return

        # All 3 attempts failed to confirm.
        print("NOT CONFIRMED - could not reproduce UnicodeDecodeError after 3 attempts")

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _run(cmd):
    """Run a command, check exit code, suppress output."""
    subprocess.run(cmd, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    main()
