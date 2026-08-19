"""Probe: _reconcile_extracted_dir does not remove func_dir when abs_src is deleted.

Spec claim: "When abs_src does not exist on disk, removes the entire corresponding
extracted-function directory and all files within it."

Actual behavior: The function empties func_dir (removes files and prunes subdirs)
but leaves func_dir itself on disk.

This probe creates a temp workspace with a populated extracted-functions directory,
calls _reconcile_extracted_dir with a non-existent abs_src, and verifies that
func_dir is NOT removed (confirming the bug).
"""

import os
import sys
import tempfile
import shutil

# Ensure repo root is on sys.path so 'src' is importable
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _reconcile_extracted_dir
except Exception as e:
    print(f"ERROR: Failed to import _reconcile_extracted_dir: {e}")
    sys.exit(1)

def main():
    # Create a fresh temp directory as the probe workspace (per FM-Agent self-validation guard)
    tmp = tempfile.mkdtemp(prefix="probe_reconcile_")
    proj_dir = os.path.join(tmp, "mock_proj")

    # Create the extracted-functions directory structure for a source file "src/foo.py"
    func_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions", "src", "foo-py")
    sub_dir = os.path.join(func_dir, "nested")

    os.makedirs(sub_dir, exist_ok=True)

    # Create some dummy extracted files to be cleaned up
    with open(os.path.join(func_dir, "bar.py"), "w") as f:
        f.write("# extracted function bar")
    with open(os.path.join(func_dir, "bar.py.spec.json"), "w") as f:
        f.write('{"spec": "bar"}')
    with open(os.path.join(func_dir, "bar.py.info.json"), "w") as f:
        f.write('{"info": "bar"}')
    with open(os.path.join(sub_dir, "baz.py"), "w") as f:
        f.write("# extracted function baz")
    with open(os.path.join(sub_dir, "baz.py.spec.json"), "w") as f:
        f.write('{"spec": "baz"}')

    # abs_src points to a source file that does NOT exist (simulating deletion)
    abs_src = os.path.join(proj_dir, "src", "foo.py")  # deliberately not created

    try:
        _reconcile_extracted_dir(proj_dir, abs_src)
    except Exception as e:
        print(f"ERROR: _reconcile_extracted_dir raised: {e}")
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(1)

    # Now check: per the spec, func_dir SHOULD be removed (and therefore not exist).
    # The bug is that the code does NOT remove func_dir.
    func_dir_exists = os.path.isdir(func_dir)

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)

    if func_dir_exists:
        print("CONFIRMED — func_dir still exists after reconcile (spec requires removal)")
    else:
        print("NOT CONFIRMED — func_dir was removed as expected by spec")

if __name__ == "__main__":
    main()
