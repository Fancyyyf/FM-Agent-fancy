# Bug Report: _deduplicate_phases

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- phases.json is overwritten with every source file path appearing in at
    most one module across all phases.
  - For any source file path appearing in multiple modules (across the same
    or different phases), only the first occurrence  in ascending phase
    number order, then module order within each phase  is preserved; all
    subsequent occurrences are removed from their respective module's
    source_files list.
  - The set of phases and modules is unchanged: no phase or module is
    removed, even when a module's source_files becomes empty.
  - Phase numbers, module names, and the ordering of phases/modules within
    phases.json are preserved.
  - Returns a dict with the key "modified_modules" mapping to a list of
    dicts, one per module from which at least one source file was removed.
    Each module dict contains: "phase" (int  the phase number), "module"
    (str  the module name), "removed_files" (list of strings  the
    deduplicated file paths that were removed), and "source_files" (list of
    strings  the module's remaining source files after deduplication).
  - Returns {"modified_modules": []} when no duplicate source files exist
    across modules.

---

### Actual Behavior

If the function returns a value R without raising an exception, the following properties hold: (1) The file at os.path.join(phases_dir, 'phases.json') has been overwritten with a JSON object data such that data['phases'] is a list of the same length and order as in the original data; for each phase p in data['phases'], p['phase'] equals the original integer, and p['modules'] is the original list of modules in the same order; for each module m in p['modules'], m['name'] is unchanged, and m['source_files'] is the subsequence of the original m['source_files'] containing exactly those files that were not in the set Seen constructed by iterating phases sorted by phase ascending and modules in their original order, with Seen growing as files are encountered for the first time; thus every source file path that ever appears in the original data appears in exactly one module's source_files list in data, specifically the first module (by phase, then module order) that originally claimed it, and the relative order of kept files in each module is preserved. (2) No phases or modules are added, removed, or reordered. (3) R is a dict with key 'modified_modules'; R['modified_modules'] is a list of objects, one per module whose source_files list changed (i.e., some file was removed), ordered by the same traversal; each object has 'phase': integer phase number, 'module': module name string (or '' if missing), 'removed_files': list of removed file paths, and 'source_files': the final deduplicated list for that module. All changed modules are included, and unchanged modules are omitted. (4) Side effect: for each duplicate file found, logging.info() was called with a message indicating the file path, phase, and module. (5) If an exception is raised before the 'with open(..., "w")' block, the original file remains unchanged and the function does not return. If an exception is raised during the final write, the file state is unspecified (may be partially written or unmodified). Return value: modified_modules list spec mismatch - deduplication gap on removed_files duplicates

---

## Code Evidence

Line 32: removed_files = [sf for sf in original if sf not in deduped]

---

## Trigger Condition

removed_files may contain duplicate file paths if the original source_files list in a module contained duplicate entries of a file that is entirely removed from that module. The specification requires the list of removed files to be deduplicated, i.e., each distinct file path should appear at most once.

---

## How to trigger the bug

When a module's `source_files` list contains duplicate entries of the same file path, and that file path is entirely removed from the module (because a prior module already claimed it), the list comprehension that builds `removed_files` preserves those duplicates. The spec requires `removed_files` to be a deduplicated list — each distinct file path should appear at most once.

### Inputs

| Parameter | Value |
|-----------|-------|
| phases_dir (temp dir containing phases.json) | A temporary directory with `phases.json` containing two modules: module_a with `["a.py", "b.py"]` and module_b with `["a.py", "a.py", "c.py"]` (both in phase 1) |

### Expected (spec-correct) Output

`removed_files` for module_b should be `["a.py"]` (unique entries only)

### Actual (buggy) Output

`removed_files` for module_b is `["a.py", "a.py"]` (duplicate entries preserved)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os, json, tempfile
sys.path.insert(0, os.getcwd())
from src.pipeline_setup import _deduplicate_phases

with tempfile.TemporaryDirectory() as tmpdir:
    with open(os.path.join(tmpdir, "phases.json"), "w") as f:
        json.dump({
            "phases": [{
                "phase": 1,
                "modules": [
                    {"name": "module_a", "source_files": ["a.py", "b.py"]},
                    {"name": "module_b", "source_files": ["a.py", "a.py", "c.py"]}
                ]
            }]
        }, f)
    result = _deduplicate_phases(tmpdir)
    for mod in result["modified_modules"]:
        if mod["module"] == "module_b":
            print(mod["removed_files"])
            # actual (buggy) output: ['a.py', 'a.py']
            # expected (correct) output: ['a.py']
```

---

## Probe Script

```python
"""
Probe script for bug: src--pipeline_setup-py--_deduplicate_phases

Bug: _deduplicate_phases() returns duplicate file paths in removed_files
when the original source_files list in a module contains duplicate entries
of a file that is entirely removed from that module.
"""
import sys
import os
import json
import tempfile

# The probe runs from the repo root — add it to the path for src/ imports
REPO_ROOT = os.getcwd()
sys.path.insert(0, REPO_ROOT)

try:
    from src.pipeline_setup import _deduplicate_phases

    # Set up a temp workspace with a phases.json that has duplicate entries
    with tempfile.TemporaryDirectory(prefix="probe_dedup_") as tmpdir:
        phases_json_path = os.path.join(tmpdir, "phases.json")

        # Module A (phase 1) claims "a.py" first
        # Module B (phase 1, same or later) has ["a.py", "a.py", "c.py"] -
        # "a.py" appears twice, and since "a.py" was already claimed by Module A,
        # it will be entirely removed from Module B.
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [
                        {
                            "name": "module_a",
                            "source_files": ["a.py", "b.py"]
                        },
                        {
                            "name": "module_b",
                            "source_files": ["a.py", "a.py", "c.py"]
                        }
                    ]
                }
            ]
        }

        with open(phases_json_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        result = _deduplicate_phases(tmpdir)

        # Find module_b's entry in modified_modules
        mod_b_entry = None
        for mod in result.get("modified_modules", []):
            if mod.get("module") == "module_b":
                mod_b_entry = mod
                break

        if mod_b_entry is None:
            print("ERROR: module_b not found in modified_modules")
            sys.exit(1)

        removed = mod_b_entry.get("removed_files", [])
        expected_unique = sorted(set(removed))
        has_duplicates = len(removed) != len(set(removed))

        if has_duplicates:
            print(
                f"CONFIRMED — duplicate removed_files for module_b: "
                f"actual={removed!r} | expected (unique)={expected_unique!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — removed_files already unique: "
                f"actual={removed!r}"
            )

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — duplicate removed_files for module_b: actual=['a.py', 'a.py'] | expected (unique)=['a.py']
```
