"""Probe script: run_entry_pipeline mutates proj_dir by creating proj_dir/fm_agent/.

Spec claim: "proj_dir is never mutated; all filesystem mutations are confined to
temporary copies that are discarded before return, regardless of success or failure"

This probe verifies whether proj_dir/fm_agent/ exists after run_entry_pipeline returns.
"""
import os
import sys
import shutil
import tempfile

# Ensure the package can be imported from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import run_entry_pipeline

    # Create a minimal project under a temp directory
    proj_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
    with open(os.path.join(proj_dir, "src", "mymod.py"), "w") as f:
        f.write("def hello():\n    return 42\n")

    # Call run_entry_pipeline — the function under test
    run_entry_pipeline(proj_dir=proj_dir, entry_func="src::mymod-py::hello")

    # Check mutation: did proj_dir/fm_agent/ get created?
    actual = os.path.isdir(os.path.join(proj_dir, "fm_agent"))
    # Spec says proj_dir is never mutated → fm_agent should NOT exist
    expected = False
    passed = actual != expected  # True → bug reproduced (actual mutation, spec says none)

    shutil.rmtree(proj_dir, ignore_errors=True)

except Exception as e:
    # Even on exception, check if proj_dir/fm_agent/ exists
    # (the finally block in _run_entry_pipeline_inner copies back partial results)
    fm_agent_exists = os.path.isdir(os.path.join(proj_dir, "fm_agent"))
    actual = fm_agent_exists
    expected = False
    passed = actual != expected
    print(f"ERROR: {e}")

if passed:
    print(f"CONFIRMED — actual: proj_dir/fm_agent exists={actual!r} | expected: exists={expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: proj_dir/fm_agent exists={actual!r}")
