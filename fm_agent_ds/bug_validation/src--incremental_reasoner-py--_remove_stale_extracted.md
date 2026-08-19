# Bug Report: _remove_stale_extracted

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/incremental_reasoner-py/_remove_stale_extracted.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Removes extracted function files from extracted_functions/ that no longer correspond to an existing source function. For every function listed under 'removed' in modified_functions, the corresponding extracted function file and its adjacent .spec.json and .info.json sidecars are deleted from disk. For every source file whose functions are ALL listed as removed (i.e. the source file is deleted or became empty of functions), the entire extracted directory corresponding to that source file under extracted_functions/ is removed, including any remaining sidecar files. Additionally, every source file registered in the current project pipeline configuration is also reconciled: any extracted function file under its corresponding extracted directory whose source function does not exist in the current state of that source file is removed, together with its sidecar files; if after reconciliation an extracted directory contains no remaining extracted function files, the directory itself is removed. Extracted function files for functions listed as 'added' or 'modified' in modified_functions are NOT removed. After reconciliation, every remaining file under extracted_functions/ corresponds to a source function that exists in a tracked source file in the current state of the repository — no orphaned extracted function files remain.

---

### Actual Behavior

The function returns normally without uncaught exceptions. Let PHASES_FILES be the set of absolute paths of source files parsed from `phases.json` (converted from relative paths using `proj_dir` as base) if `_load_phases` succeeds, otherwise let PHASES_FILES be the empty set. Let S = set(modified_functions.keys()) ∪ PHASES_FILES. For every path `abs_src` in S, the extracted-function directory `D` associated with `abs_src` (located under `proj_dir/extracted_functions/`) has been updated as follows: (a) if `abs_src` exists on disk, `D` contains only those extracted function files (and their `.spec.json` and `.info.json` sidecar files) whose functions are currently present in the source file at `abs_src`; any stale extracted function files and their sidecars have been removed, and if `D` becomes empty after these removals, `D` itself is removed; (b) if `abs_src` does not exist on disk, `D` and all its contents are entirely removed if they existed. No other files or directories outside the extracted-function directory tree are modified. The source files at each `abs_src` are not altered.

---

## Code Evidence

Line 14: `srcs = set(modified_functions)  ;`  Line 23: `for abs_src in srcs:  ;`  Line 24: `        _reconcile_extracted_dir(proj_dir, abs_src)`

---

## Trigger Condition

The code only reconciles source file paths present in the union of modified_functions keys and the phases.json source files. It does not visit or clean up extracted directories for source files that are no longer tracked (not in the pipeline and not present in modified_functions). The specification requires that after reconciliation every remaining file under extracted_functions/ corresponds to a source function that exists in a tracked source file, i.e., no orphaned extracted function files remain. By failing to remove extracted directories for untracked source files, the code's behavior (Condition A) violates Condition B.

---

## How to trigger the bug

A source file previously existed in the pipeline (phases.json) and had extracted function files generated. The file is then removed from phases.json (untracked) and the source file itself is also deleted. Since the file is not in `modified_functions` (it wasn't part of the diff between the old and new commit — it was simply removed from the pipeline config), and it is no longer in `phases.json`, the function `_remove_stale_extracted` never visits its extracted directory. The extracted function files and their sidecars remain as orphans.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | temporary directory with `fm_agent/phases.json`, `src/tracked.py`, and `fm_agent/extracted_functions/old/untracked-py/` containing stale files |
| `modified_functions` | `{}` (empty — no modified functions) |

### Expected (spec-correct) Output

The orphan extracted directory `fm_agent/extracted_functions/old/untracked-py/` is removed, along with all contained function files and sidecar files. No orphaned extracted file remains.

### Actual (buggy) Output

The orphan extracted directory and all its files (`old_func.py`, `old_func.py.spec.json`, `old_func.py.info.json`) remain on disk. The directory was never visited because its source path is absent from both `modified_functions` and `phases.json`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile, shutil
from src.incremental_reasoner import _remove_stale_extracted

proj_dir = tempfile.mkdtemp()
os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
os.makedirs(os.path.join(proj_dir, "fm_agent", "extracted_functions", "old", "untracked-py"), exist_ok=True)

# A phases.json that does NOT reference old/untracked.py
with open(os.path.join(proj_dir, "fm_agent", "phases.json"), "w") as f:
    json.dump({"phases": [{"name": "p1", "modules": [{"name": "m1", "source_files": ["src/tracked.py"]}]}]}, f)

# Stale extracted files for an untracked source file
orphan_dir = os.path.join(proj_dir, "fm_agent", "extracted_functions", "old", "untracked-py")
with open(os.path.join(orphan_dir, "old_func.py"), "w") as f: f.write("pass\n")
with open(os.path.join(orphan_dir, "old_func.py.spec.json"), "w") as f: json.dump({}, f)
with open(os.path.join(orphan_dir, "old_func.py.info.json"), "w") as f: json.dump({}, f)

_remove_stale_extracted(proj_dir, {})
print(os.listdir(orphan_dir))  # ['old_func.py', 'old_func.py.spec.json', 'old_func.py.info.json'] — NOT empty!
# expected: directory should be removed
shutil.rmtree(proj_dir)
```

---

## Probe Script

```python
"""
Probe script for bug: _remove_stale_extracted does not clean up extracted
directories for source files not tracked in phases.json and not present in
modified_functions, leaving orphaned extracted function files.

Bug ID: src--incremental_reasoner-py--_remove_stale_extracted

Scenario:
  - Source file old/untracked.py once existed and had extracted functions.
  - It was removed from phases.json (pipeline config) and the file itself
    was deleted — so it is in neither modified_functions nor phases.json.
  - _remove_stale_extracted should remove its stale extracted directory,
    but the current code never visits it, so orphans remain.
"""

import json
import os
import shutil
import sys
import tempfile

# Ensure the repo root is on sys.path so `from src.incremental_reasoner`
# resolves.  The probe runs from the repo root, but the script's directory
# (fm_agent/bug_validation/) would otherwise shadow the root import.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))
sys.path.insert(0, _repo_root)

try:
    from src.incremental_reasoner import _remove_stale_extracted
except ImportError as e:
    print(f"ERROR: cannot import _remove_stale_extracted: {e}")
    sys.exit(1)


def main():
    """Set up a minimal project tree, run _remove_stale_extracted, assert result."""

    # ── 1. Build a temporary project directory ────────────────────────────
    proj_dir = tempfile.mkdtemp(prefix="fm_agent_probe_")
    try:
        # phases.json tracked source file — NOT the orphan
        tracked_rel = "src/tracked.py"
        tracked_abs = os.path.abspath(os.path.join(proj_dir, tracked_rel))

        # The orphan source file that was removed from the pipeline:
        #   - was previously in phases.json → extracted functions exist
        #   - is now deleted from disk
        #   - removed from phases.json
        #   - not in modified_functions (wasn't modified; was just un-tracked)
        orphan_rel = "old/untracked.py"
        orphan_abs = os.path.abspath(os.path.join(proj_dir, orphan_rel))

        # Compute the extracted-function directory for the orphan file
        extracted_base = os.path.join(proj_dir, "fm_agent", "extracted_functions")
        orphan_dir_name = orphan_rel.rsplit(".", 1)[0].replace("/", "-").replace(".", "-")
        orphan_func_dir = os.path.join(extracted_base, "old", "untracked-py")
        # Actually, let's use _src_rel_to_func_dir if accessible, or hardcode:
        # old/untracked.py → extracted_functions/old/untracked-py/

        # ── 2. Create the tracked source file (so phases.json is valid) ──
        os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
        with open(tracked_abs, "w") as f:
            f.write("def tracked_func():\n    return 1\n")

        # ── 3. Create phases.json that ONLY lists the tracked file ────────
        os.makedirs(os.path.join(proj_dir, "fm_agent"), exist_ok=True)
        phases = {
            "phases": [
                {
                    "name": "test-phase",
                    "modules": [
                        {
                            "name": "test_module",
                            "source_files": [tracked_rel],
                        }
                    ],
                }
            ]
        }
        with open(os.path.join(proj_dir, "fm_agent", "phases.json"), "w") as f:
            json.dump(phases, f)

        # ── 4. Create stale extracted-function files for the orphan ───────
        os.makedirs(orphan_func_dir, exist_ok=True)

        orphan_func_file = os.path.join(orphan_func_dir, "old_func.py")
        orphan_spec_file = orphan_func_file + ".spec.json"
        orphan_info_file = orphan_func_file + ".info.json"

        with open(orphan_func_file, "w") as f:
            f.write("def old_func():\n    pass\n")
        with open(orphan_spec_file, "w") as f:
            json.dump({"pre": "true", "post": "true"}, f)
        with open(orphan_info_file, "w") as f:
            json.dump({"fqn": "old_func", "file": "old/untracked.py"}, f)

        # Sanity: files exist before the call
        assert os.path.isfile(orphan_func_file), "orphan func file missing"
        assert os.path.isfile(orphan_spec_file), "orphan spec file missing"
        assert os.path.isfile(orphan_info_file), "orphan info file missing"

        # ── 5. Call _remove_stale_extracted ───────────────────────────────
        #  modified_functions is empty — the orphan source is not there
        _remove_stale_extracted(proj_dir, {})

        # ── 6. Assert ─────────────────────────────────────────────────────
        # Specification claim: every remaining file under extracted_functions/
        # corresponds to a source function that exists in a tracked source
        # file. The orphan file path is neither in phases.json nor in
        # modified_functions, so it is untracked. Its extracted files should
        # be removed.
        stale_remain = os.path.isfile(orphan_func_file)
        spec_remain = os.path.isfile(orphan_spec_file)
        info_remain = os.path.isfile(orphan_info_file)

        expected_removed = not stale_remain and not spec_remain and not info_remain
        actual_stale = stale_remain or spec_remain or info_remain

        if actual_stale:
            print(
                "CONFIRMED"
                f" — orphan extracted files remain after _remove_stale_extracted"
                f" (func_file={stale_remain}, spec={spec_remain}, info={info_remain})"
                f" | expected: all removed (orphans cleaned)"
            )
        else:
            print(
                "NOT CONFIRMED"
                f" — all orphan extracted files were removed as expected"
                f" (func_file={stale_remain}, spec={spec_remain}, info={info_remain})"
            )

    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    finally:
        # Clean up temp dir
        shutil.rmtree(proj_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — orphan extracted files remain after _remove_stale_extracted (func_file=True, spec=True, info=True) | expected: all removed (orphans cleaned)
```
