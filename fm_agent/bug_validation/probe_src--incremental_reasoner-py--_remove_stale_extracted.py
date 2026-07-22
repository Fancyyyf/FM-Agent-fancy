import sys
import os
import json
import tempfile
import shutil

# Import the function under test from the FM-Agent source.
# The workspace root is the snapshot directory (repo root for imports).
# The probe runs from the repo root; ensure the source package is importable.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)
from src.incremental_reasoner import _remove_stale_extracted

# ── Create a fresh temporary workspace ──────────────────────────────────────
tmp = tempfile.mkdtemp(prefix="bv_rm_stale_")
proj_dir = os.path.join(tmp, "project")
src_dir = os.path.join(proj_dir, "pkg")

os.makedirs(src_dir, exist_ok=True)

# ── phases.json ─────────────────────────────────────────────────────────────
fm_agent_dir = os.path.join(proj_dir, "fm_agent")
os.makedirs(fm_agent_dir, exist_ok=True)
phases_data = {
    "phases": [
        {
            "phase": 1,
            "modules": [
                {
                    "name": "test_module",
                    "source_files": ["pkg/a.py", "pkg/b.py"]
                }
            ]
        }
    ]
}
with open(os.path.join(fm_agent_dir, "phases.json"), "w") as f:
    json.dump(phases_data, f)

# ── Stale extracted-function directories (source files are DELETED) ─────────
# They share the common parent directory  fm_agent/extracted_functions/pkg/
extracted_base = os.path.join(fm_agent_dir, "extracted_functions")

for name in ("a", "b"):
    func_dir = os.path.join(extracted_base, f"pkg/{name}-py")
    os.makedirs(func_dir, exist_ok=True)
    stale_file = os.path.join(func_dir, f"stale_func.py")
    with open(stale_file, "w") as f:
        f.write("# stale extracted function\n")

    # Also create a "deleted" source path that does NOT exist on disk.
    # The probe does not create pkg/a.py or pkg/b.py, so they are absent.

# ── modified_functions: both source files are "removed" ─────────────────────
modified_functions = {
    os.path.abspath(os.path.join(proj_dir, "pkg", "a.py")): {"removed": ["stale_func"]},
    os.path.abspath(os.path.join(proj_dir, "pkg", "b.py")): {"removed": ["stale_func"]},
}

# ── Call the function under test ────────────────────────────────────────────
_remove_stale_extracted(proj_dir, modified_functions)

# ── Verify: the spec requires that empty parent directories be pruned ───────
#
# The spec (spec_claim) says:
#   "...any empty parent directories are pruned."
#
# _reconcile_extracted_dir removes stale FILES from func_dir and prunes
# subdirectories within func_dir, but never removes func_dir itself
# (see the `root != func_dir` guard on line 526). After both a-py/ and
# b-py/ had all their files removed:
#   - a-py/ and b-py/ remain as EMPTY directories (should be removed)
#   - their shared parent pkg/ thus still has children (should be empty & pruned)
# Both conditions violate the spec.

a_py_dir = os.path.join(extracted_base, "pkg", "a-py")
b_py_dir = os.path.join(extracted_base, "pkg", "b-py")
pkg_dir = os.path.join(extracted_base, "pkg")

a_stale = os.path.isdir(a_py_dir) and len(os.listdir(a_py_dir)) == 0
b_stale = os.path.isdir(b_py_dir) and len(os.listdir(b_py_dir)) == 0

bug_confirmed = a_stale and b_stale

if bug_confirmed:
    print(f"CONFIRMED — empty func directories a-py and b-py left behind; parent pkg/ not pruned. Spec requires pruning all empty parent directories.")
else:
    details = []
    if not os.path.isdir(a_py_dir):
        details.append("a-py was removed")
    elif not a_stale:
        details.append(f"a-py not empty: {os.listdir(a_py_dir)}")
    if not os.path.isdir(b_py_dir):
        details.append("b-py was removed")
    elif not b_stale:
        details.append(f"b-py not empty: {os.listdir(b_py_dir)}")
    print(f"NOT CONFIRMED — {', '.join(details)}")

# ── Cleanup ─────────────────────────────────────────────────────────────────
shutil.rmtree(tmp, ignore_errors=True)
