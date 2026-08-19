#!/usr/bin/env python3
"""
Probe script for bug: src--incremental_reasoner-py--_verify_incremental_functions

Bug: os.path.splitext(rel)[0] strips only the last extension, so two extracted
function files with the same stem but different extensions in the same directory
map to the same verdict file path (e.g., both 'foo.py' and 'foo.c' → 'foo.json').

This test creates a simulated extracted-functions directory containing two files
in the same directory that share a stem but have different extensions, then
applies the exact same path-derivation logic used in the buggy code at
src/incremental_reasoner.py line 2114 to verify the collision.
"""
import os
import sys
import tempfile
import shutil

def test_path_collision():
    """
    Simulate the scenario where two extracted function files in the same
    directory share a stem but have different extensions. The buggy code at
    src/incremental_reasoner.py:2114 uses:

        stale = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")

    If 'rel' is something like 'somedir/myfunction.py' and 'somedir/myfunction.c',
    both produce 'somedir/myfunction.json' → collision.
    """
    # Create a temporary directory simulating extracted_functions with a
    # subdirectory containing two files with different extensions.
    tmpdir = tempfile.mkdtemp(prefix="bug_probe_")
    try:
        extracted_dir = os.path.join(tmpdir, "extracted_functions")
        output_dir = os.path.join(tmpdir, "logic_verification_results")
        os.makedirs(output_dir, exist_ok=True)

        # Simulate a typical extracted-function directory structure.
        # In a real project, this would be like extracted_functions/src/foo-py/
        # or extracted_functions/src/foo-c/. But the bug manifests when two
        # files end up in the SAME directory with different extensions —
        # which could happen if the directory naming scheme changes or if
        # updated_spec_files provides paths that collide.
        func_dir = os.path.join(extracted_dir, "somedir", "mymodule")
        os.makedirs(func_dir, exist_ok=True)

        # Create two extracted function files with different extensions
        # but the same stem, both in the same directory.
        file1 = os.path.join(func_dir, "myfunction.py")
        file2 = os.path.join(func_dir, "myfunction.c")
        with open(file1, "w") as f:
            f.write("# Function A\n")
        with open(file2, "w") as f:
            f.write("// Function B\n")

        # Compute relative paths as the buggy code does
        rel1 = os.path.relpath(file1, extracted_dir)
        rel2 = os.path.relpath(file2, extracted_dir)

        print(f"Relative path 1: {rel1!r}")
        print(f"Relative path 2: {rel2!r}")
        print(f"Same basename?  {os.path.basename(rel1).rsplit('.', 1)[0] == os.path.basename(rel2).rsplit('.', 1)[0]}")

        # Apply the EXACT same path derivation as the buggy code (line 2114):
        #   stale = os.path.join(output_dir, os.path.splitext(rel)[0] + ".json")
        stale1 = os.path.join(output_dir, os.path.splitext(rel1)[0] + ".json")
        stale2 = os.path.join(output_dir, os.path.splitext(rel2)[0] + ".json")

        print(f"\nBuggy path derivation (splitext → .json):")
        print(f"  File 1 → {stale1!r}")
        print(f"  File 2 → {stale2!r}")
        print(f"  Collision?  {stale1 == stale2}")

        # The spec requires each function to have a UNIQUE verdict file path.
        # Two different functions mapping to the same path violates the spec.
        collision = stale1 == stale2

        # Also test: splitext strips ONLY the last extension, so a file like
        # "helper.spec.json" would become "helper.spec.json" after splitext:
        # splitext("helper.spec.json")[0] = "helper.spec" (not "helper")
        rel3 = "somedir/mymodule/helper.py"
        rel4 = "somedir/mymodule/helper.py.spec.json"  # metadata sidecar
        print(f"\nsplitext on metadata sidecars:")
        print(f"  splitext({rel3!r})[0] = {os.path.splitext(rel3)[0]!r}")
        print(f"  splitext({rel4!r})[0] = {os.path.splitext(rel4)[0]!r}")
        print(f"  Note: metadata sidecars use .spec.json suffix, but")
        print(f"  file_list excludes them via _is_metadata_sidecar filter.")

        if collision:
            print("\nCONFIRMED — os.path.splitext(rel)[0] produces identical "
                  "verdict file paths for two distinct extracted-function files "
                  "with the same stem but different extensions in the same directory.")
        else:
            print("\nNOT CONFIRMED — paths are unique. Collision did not occur.")

        return collision

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_bug_id_collision():
    """
    Also test the bug_id derivation at line 2180:
        bug_id = os.path.splitext(rel)[0].replace(os.sep, "--").replace("/", "--")

    If two files in the same directory share a stem but different extensions,
    they produce the same bug_id → collision in bug_validation result files.
    """
    # Same scenario: two files with different extensions in the same dir
    rel1 = "somedir/mymodule/myfunction.py"
    rel2 = "somedir/mymodule/myfunction.c"

    bug_id1 = os.path.splitext(rel1)[0].replace(os.sep, "--").replace("/", "--")
    bug_id2 = os.path.splitext(rel2)[0].replace(os.sep, "--").replace("/", "--")

    print(f"\nBug ID derivation (line 2180):")
    print(f"  rel {rel1!r} → bug_id {bug_id1!r}")
    print(f"  rel {rel2!r} → bug_id {bug_id2!r}")
    print(f"  Collision? {bug_id1 == bug_id2}")

    return bug_id1 == bug_id2


if __name__ == "__main__":
    try:
        result1 = test_path_collision()
        result2 = test_bug_id_collision()

        # The bug is CONFIRMED if EITHER path derivation or bug_id derivation
        # produces a collision for two distinct function files.
        if result1 or result2:
            print("\nFINAL VERDICT: CONFIRMED — os.path.splitext produces "
                  "ambiguous paths/bug_ids when two extracted-function files "
                  "in the same directory share a stem but different extensions.")
        else:
            print("\nFINAL VERDICT: NOT CONFIRMED — no collision detected "
                  "in the path or bug_id derivation.")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
