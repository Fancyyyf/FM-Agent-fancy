"""Probe script: verify stage_domain_knowledge_files returns "/"-separated paths.

Bug claim: The specification requires returned paths to use '/' as the path separator
regardless of platform, but the code returns the raw output of
list_staged_domain_knowledge_relpaths, which may use OS-specific separators.

This probe creates a temp directory with staged domain knowledge files, calls the
relevant functions, and verifies all returned paths use "/" as the separator.
It also monkey-patches os.sep and os.path.relpath to simulate a non-"/" platform
(Windows-style backslashes) to prove the replace() call handles the conversion.
"""

import os
import sys
import tempfile
import shutil

# Add project root to path so we can import the entry-point module
PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
while not os.path.isfile(os.path.join(PROJ_DIR, "pyproject.toml")):
    parent = os.path.dirname(PROJ_DIR)
    if parent == PROJ_DIR:
        sys.exit("ERROR: could not find project root")
    PROJ_DIR = parent

sys.path.insert(0, PROJ_DIR)

# Import via entry point (src.domain_knowledge)
try:
    from src.domain_knowledge import (
        list_staged_domain_knowledge_relpaths,
        stage_domain_knowledge_files,
        USER_KNOWLEDGE_REL_DIR,
        USER_KNOWLEDGE_MANIFEST,
    )
except Exception as e:
    print(f"ERROR: import failed: {e}")
    sys.exit(1)


def test_on_linux():
    """Test on native Linux (os.sep == '/')."""
    tmpdir = tempfile.mkdtemp(prefix="probe_")
    work_dir = os.path.join(tmpdir, "work")
    knowledge_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
    os.makedirs(knowledge_dir, exist_ok=True)

    # Create a fake .md file in the knowledge dir
    md_path = os.path.join(knowledge_dir, "test.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# test\n")

    # Test 1: list_staged_domain_knowledge_relpaths
    relpaths = list_staged_domain_knowledge_relpaths(work_dir)
    for p in relpaths:
        if "\\" in p:
            print(f"FAIL (linux): path contains backslash: {p!r}")
            return False
        if not p.startswith("fm_agent/"):
            print(f"FAIL (linux): path does not start with fm_agent/: {p!r}")
            return False
    print(f"  list_staged: {relpaths}")

    # Test 2: stage_domain_knowledge_files without markdown_paths (line 137 path)
    empty_result = stage_domain_knowledge_files(PROJ_DIR, work_dir)
    for p in empty_result:
        if "\\" in p:
            print(f"FAIL (linux): empty-result path contains backslash: {p!r}")
            return False
    print(f"  stage empty: {empty_result}")

    # Test 3: stage_domain_knowledge_files with markdown_paths (line 171 path)
    # Create a temp markdown file to stage
    tmp_md = os.path.join(tmpdir, "input.md")
    with open(tmp_md, "w", encoding="utf-8") as f:
        f.write("# input\n")

    # Remove previous knowledge dir so staging works cleanly
    shutil.rmtree(work_dir, ignore_errors=True)
    staged_result = stage_domain_knowledge_files(PROJ_DIR, work_dir, markdown_paths=[tmp_md])
    for p in staged_result:
        if "\\" in p:
            print(f"FAIL (linux): staged-result path contains backslash: {p!r}")
            return False
    print(f"  stage full: {staged_result}")

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)
    return True


def test_with_patched_separator():
    """Monkey-patch os to simulate a non-"/" platform and test the replace() call."""
    tmpdir = tempfile.mkdtemp(prefix="probe_patch_")
    work_dir = os.path.join(tmpdir, "work")
    knowledge_dir = os.path.join(work_dir, USER_KNOWLEDGE_REL_DIR)
    os.makedirs(knowledge_dir, exist_ok=True)

    # Create a fake .md file
    md_path = os.path.join(knowledge_dir, "test.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# test\n")

    # Monkey-patch: simulate Windows backslash paths
    orig_sep = os.sep
    orig_relpath = os.path.relpath
    orig_join = os.path.join
    orig_isdir = os.path.isdir

    try:
        os.sep = "\\"
        os.path.sep = "\\"

        def fake_relpath(path, start):
            """Return relative path with backslash separators."""
            result = orig_relpath(path, start)
            return result.replace("/", "\\")

        os.path.relpath = fake_relpath

        # Now call list_staged_domain_knowledge_relpaths
        relpaths = list_staged_domain_knowledge_relpaths(work_dir)

        # The function should have converted backslashes to "/" via replace(os.sep, "/")
        for p in relpaths:
            if "\\" in p:
                print(f"FAIL (patched): path contains backslash after conversion: {p!r}")
                print(f"  The replace(os.sep, '/') at domain_knowledge.py:124 should have")
                print(f"  converted all backslashes. Bug CONFIRMED.")
                return False
            if not p.startswith("fm_agent/"):
                print(f"FAIL (patched): path does not start with fm_agent/: {p!r}")
                return False
            if "/" not in p[len("fm_agent/"):]:
                print(f"WARN (patched): path has no '/' separators after prefix: {p!r}")
                # This is ok — a single-level path would just be "fm_agent/file.md"
        print(f"  patched list_staged: {relpaths}")
        return True
    finally:
        os.sep = orig_sep
        os.path.sep = orig_sep
        os.path.relpath = orig_relpath
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    all_passed = True

    # Test 1: Linux native
    print("--- Test 1: Linux native (os.sep='/') ---")
    try:
        if test_on_linux():
            print("PASS: Linux native test — all paths use '/' separators")
        else:
            all_passed = False
    except Exception as e:
        print(f"FAIL: Linux native test crashed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # Test 2: Patched separator
    print("\n--- Test 2: Patched os (os.sep='\\\\') ---")
    try:
        if test_with_patched_separator():
            print("PASS: Patched test — replace(os.sep, '/') correctly converted backslashes")
        else:
            all_passed = False
    except Exception as e:
        print(f"FAIL: Patched test crashed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    if all_passed:
        print("\nNOT CONFIRMED — The code already converts paths to '/' separators")
        print("  through list_staged_domain_knowledge_relpaths's replace(os.sep, '/') call at line 124.")
        print("  Both stage_domain_knowledge_files return paths (lines 137 and 171) delegate to")
        print("  list_staged_domain_knowledge_relpaths, which handles the conversion.")
        sys.exit(0)
    else:
        print("\nCONFIRMED — Bug reproduced: paths contain non-'/' separators")
        sys.exit(0)


if __name__ == "__main__":
    main()
