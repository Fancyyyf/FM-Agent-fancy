# Bug Report: _remove_stale_extracted

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- For every absolute source-file path that is either a key in modified_functions or listed in the "source_files" entries of all phases loaded from phases.json, the extracted-function tree under fm_agent/extracted_functions/ associated with that source file is reconciled with the current codegraph output. Any extracted function file or directory that no longer corresponds to a current source function (including when the source file itself is absent) is deleted, and any empty parent directories are pruned.
  - Files and directories under fm_agent/extracted_functions/ that correspond to source files not in the union of modified_functions keys and phases.json entries are unchanged.

---

### Actual Behavior

After execution, the extracted-functions subdirectory tree under fm_agent/ has been updated such that for every source file path that belongs to the union S = modified_functions.keys()  (if loading phases.json succeeded) the set of absolute paths derived from all source_files entries in modules within phases of phases.json, the extracted directory corresponding to that source file (if it exists) contains only files that are currently expected according to the function spans of that source file, any stale extracted files have been deleted, and empty subdirectories have been pruned. For any source file path not in S, no changes have been made to its extracted directory. No other side effects occur. Formal logic: Let M = dom(modified_functions). Let P =  if an OSError, ValueError, or KeyError was raised during loading of phases.json; otherwise P = { os.path.abspath(os.path.join(proj_dir, rel)) | phase  phases_data['phases'], module  phase['modules'], rel  module['source_files'] }. Then S = M  P. For each abs_src  S, the effect of _reconcile_extracted_dir(proj_dir, abs_src) has been applied, meaning: the extracted directory for abs_src (if non-existent) was left untouched; otherwise, its contents now equal the set of expected extracted file paths derived from the current source, and all stale files/directories have been removed. For abs_src  S, its extracted directory (if any) is unchanged. The function returns None.

---

## Code Evidence

Line 23: for abs_src in srcs:
Line 24:     _reconcile_extracted_dir(proj_dir, abs_src)

---

## Trigger Condition

The code only calls _reconcile_extracted_dir for each individual source file. This may leave empty parent directories (like a/) that are shared by multiple source-specific directories when all children are removed. The specification explicitly requires pruning any empty parent directories, which the code does not guarantee.

---

## How to trigger the bug

_remove_stale_extracted calls _reconcile_extracted_dir for each source file. _reconcile_extracted_dir removes stale extracted files and prunes subdirectories within `func_dir`, but explicitly does NOT remove `func_dir` itself (the `root != func_dir` guard on the pruning loop), and does NOT prune the empty parent directories above `func_dir`. When multiple deleted source files share a common parent directory under `fm_agent/extracted_functions/`, their empty `func_dir` directories are left behind, violating the spec's requirement that "any empty parent directories are pruned."

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temp project directory |
| `modified_functions` | Two absolute source paths (neither file exists on disk): `{<proj_dir>/pkg/a.py: {"removed": ["stale_func"]}, <proj_dir>/pkg/b.py: {"removed": ["stale_func"]}}` |
| `phases.json` | Contains a module with `source_files: ["pkg/a.py", "pkg/b.py"]` |
| Extracted tree | `fm_agent/extracted_functions/pkg/a-py/stale_func.py` and `fm_agent/extracted_functions/pkg/b-py/stale_func.py` exist |

### Expected (spec-correct) Output

Empty `a-py/` and `b-py/` directories should be removed, and the now-empty shared parent `pkg/` should also be pruned. No orphaned directories should remain under `fm_agent/extracted_functions/`.

### Actual (buggy) Output

`a-py/` and `b-py/` remain as empty directories under `pkg/`. The shared parent `pkg/` is not pruned because its children (`a-py/` and `b-py/`) were never removed by `_reconcile_extracted_dir`. The result is orphaned empty directories that violate the spec.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os, json, tempfile

# Add the FM-Agent source to the import path
repo_root = os.path.dirname(os.path.abspath(__file__))
import sys; sys.path.insert(0, repo_root)
from src.incremental_reasoner import _remove_stale_extracted

# Set up a project with stale extracted directories under a shared parent
tmp = tempfile.mkdtemp()
proj_dir = os.path.join(tmp, "project")
os.makedirs(os.path.join(proj_dir, "pkg"))

fm = os.path.join(proj_dir, "fm_agent")
os.makedirs(fm)
with open(os.path.join(fm, "phases.json"), "w") as f:
    json.dump({"phases": [{"phase": 1, "modules": [{"name": "m", "source_files": ["pkg/a.py", "pkg/b.py"]}]}]}, f)

ext = os.path.join(fm, "extracted_functions")
for name in ("a", "b"):
    d = os.path.join(ext, f"pkg/{name}-py")
    os.makedirs(d)
    with open(os.path.join(d, "stale_func.py"), "w") as f:
        f.write("# stale")

# Source files pkg/a.py and pkg/b.py do NOT exist (deleted)
modified = {
    os.path.abspath(os.path.join(proj_dir, "pkg/a.py")): {"removed": ["stale_func"]},
    os.path.abspath(os.path.join(proj_dir, "pkg/b.py")): {"removed": ["stale_func"]},
}

_remove_stale_extracted(proj_dir, modified)

# Check: empty func directories remain
a_py = os.path.join(ext, "pkg/a-py")
b_py = os.path.join(ext, "pkg/b-py")
print("a-py still exists:", os.path.isdir(a_py))  # True (BUG)
print("b-py still exists:", os.path.isdir(b_py))  # True (BUG)
# actual (buggy) output: both a-py and b-py remain as empty directories
# expected (correct) output: both removed, pkg/ pruned
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — empty func directories a-py and b-py left behind; parent pkg/ not pruned. Spec requires pruning all empty parent directories.
```
