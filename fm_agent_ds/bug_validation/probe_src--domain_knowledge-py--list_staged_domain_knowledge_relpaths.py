"""Probe script for bug: list_staged_domain_knowledge_relpaths OSError handling.

Bug claim: The function can raise OSError (e.g., PermissionError) when os.walk
encounters an unreadable subdirectory, violating the spec that it must always
return a (possibly empty) list.

Test: Create a staging directory with a permission-restricted subdirectory and
call the function through the public entry point.
"""
import os
import stat
import sys
import tempfile
import shutil

# Add repo root to sys.path so "from src.domain_knowledge import ..." works
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from src.domain_knowledge import list_staged_domain_knowledge_relpaths


def test_unreadable_subdir_chmod_zero():
    """Attempt 1: chmod 0o000 on a subdirectory within the staging dir."""
    td = tempfile.mkdtemp()
    try:
        kn_dir = os.path.join(td, "spec_prompts", "domain_context", "user_knowledge")
        os.makedirs(kn_dir)
        # Add a valid markdown file
        with open(os.path.join(kn_dir, "test.md"), "w") as f:
            f.write("# Test\n")
        # Create an unreadable subdirectory
        restricted = os.path.join(kn_dir, "restricted")
        os.makedirs(restricted)
        with open(os.path.join(restricted, "hidden.md"), "w") as f:
            f.write("# Hidden\n")
        os.chmod(restricted, 0o000)

        try:
            result = list_staged_domain_knowledge_relpaths(td)
            return False, f"Returned normally: {result}"
        except OSError as e:
            return True, f"OSError raised: {type(e).__name__}: {e}"
        finally:
            os.chmod(restricted, stat.S_IRWXU)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_unreadable_subdir_no_execute():
    """Attempt 2: chmod 0o444 (read-only, no execute) on a subdirectory."""
    td = tempfile.mkdtemp()
    try:
        kn_dir = os.path.join(td, "spec_prompts", "domain_context", "user_knowledge")
        os.makedirs(kn_dir)
        with open(os.path.join(kn_dir, "test.md"), "w") as f:
            f.write("# Test\n")
        restricted = os.path.join(kn_dir, "restricted")
        os.makedirs(restricted)
        with open(os.path.join(restricted, "hidden.md"), "w") as f:
            f.write("# Hidden\n")
        os.chmod(restricted, 0o444)

        try:
            result = list_staged_domain_knowledge_relpaths(td)
            return False, f"Returned normally: {result}"
        except OSError as e:
            return True, f"OSError raised: {type(e).__name__}: {e}"
        finally:
            os.chmod(restricted, stat.S_IRWXU)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def test_unlistable_parent():
    """Attempt 3: Remove execute from parent directory to break path resolution."""
    td = tempfile.mkdtemp()
    try:
        kn_dir = os.path.join(td, "spec_prompts", "domain_context", "user_knowledge")
        os.makedirs(kn_dir)
        with open(os.path.join(kn_dir, "test.md"), "w") as f:
            f.write("# Test\n")

        # Remove execute from parent of user_knowledge
        dc_dir = os.path.join(td, "spec_prompts", "domain_context")
        os.chmod(dc_dir, 0o666)

        try:
            result = list_staged_domain_knowledge_relpaths(td)
            return False, f"Returned normally: {result}"
        except OSError as e:
            return True, f"OSError raised: {type(e).__name__}: {e}"
        finally:
            os.chmod(dc_dir, stat.S_IRWXU)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    bug_id = "src--domain_knowledge-py--list_staged_domain_knowledge_relpaths"
    confirmed = False
    last_result = ""

    tests = [
        ("chmod 0o000 subdir", test_unreadable_subdir_chmod_zero),
        ("chmod 0o444 subdir (no execute)", test_unreadable_subdir_no_execute),
        ("remove execute from parent dir", test_unlistable_parent),
    ]

    for name, test_fn in tests:
        try:
            is_bug, msg = test_fn()
            last_result = msg
            if is_bug:
                confirmed = True
                print(f"CONFIRMED — {name}: {msg}")
                break
            else:
                print(f"  [{name}]: NOT CONFIRMED — {msg}")
        except Exception as e:
            print(f"  [{name}]: ERROR — {type(e).__name__}: {e}")
            last_result = f"ERROR: {type(e).__name__}: {e}"

    if not confirmed:
        print(f"NOT CONFIRMED — All attempts failed to reproduce the bug.")
        print(f"  Last result: {last_result}")


if __name__ == "__main__":
    main()
