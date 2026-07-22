"""Probe script for bug: try_codegraph_init removes .codegraph before checking executable.

Bug ID: src--languages--codegraph-py--try_codegraph_init

The function try_codegraph_init(proj_dir, force=True) calls shutil.rmtree()
at line 526 to remove the .codegraph directory BEFORE checking whether the
codegraph executable exists (line 530-537). When codegraph is missing, a
FileNotFoundError is caught and the function returns — but the directory
has already been removed, violating the spec that requires no file
modifications when the executable is not found.
"""

import os
import sys
import tempfile
import shutil

# Ensure we can import from the repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import src.languages.codegraph as codegraph_module
from src.languages.codegraph import try_codegraph_init

# Monkey-patch _codegraph_cmd to simulate "codegraph not installed".
# This ensures subprocess.run([cmd, "init"], ...) raises FileNotFoundError
# regardless of whether codegraph is actually present on the system.
_original_codegraph_cmd = codegraph_module._codegraph_cmd
codegraph_module._codegraph_cmd = lambda: "/nonexistent/codegraph_binary_not_found"

exit_code = 0
temp_dir = None
result_msg = ""

try:
    # Create a temporary project directory with a pre-existing .codegraph/codegraph.db
    temp_dir = tempfile.mkdtemp(prefix="fmagent_probe_")
    codegraph_dir = os.path.join(temp_dir, ".codegraph")
    os.makedirs(codegraph_dir, exist_ok=True)
    db_path = os.path.join(codegraph_dir, "codegraph.db")
    with open(db_path, "w") as f:
        f.write("mock codegraph database\n")

    # Verify pre-condition: .codegraph directory and codegraph.db exist before the call
    assert os.path.isdir(codegraph_dir), (
        "Pre-condition failed: .codegraph dir does not exist"
    )
    assert os.path.exists(db_path), (
        "Pre-condition failed: codegraph.db does not exist"
    )

    # Call the function with force=True — the buggy path (line 526 removes dir
    # BEFORE line 530 checks for the codegraph executable)
    try_codegraph_init(proj_dir=temp_dir, force=True)

    # After the call, check whether .codegraph was preserved (spec-correct)
    # or removed (buggy behavior)
    dir_exists_after = os.path.isdir(codegraph_dir)

    if dir_exists_after:
        result_msg = (
            "NOT CONFIRMED — .codegraph directory was preserved (spec-compliant). "
            "The function left the directory intact when codegraph was unavailable."
        )
    else:
        result_msg = (
            "CONFIRMED — .codegraph directory was removed before checking for "
            "codegraph executable. Spec violation: the spec requires that when "
            "the codegraph executable is not found, the function returns "
            "immediately without creating, modifying, or removing any files "
            "under proj_dir."
        )

except Exception as exc:
    result_msg = f"ERROR: {type(exc).__name__}: {exc}"
    exit_code = 1

finally:
    # Restore original _codegraph_cmd
    codegraph_module._codegraph_cmd = _original_codegraph_cmd
    # Cleanup temp directory
    if temp_dir is not None and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

print(result_msg)
sys.exit(exit_code)
