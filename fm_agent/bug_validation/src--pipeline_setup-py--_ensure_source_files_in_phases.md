# Bug Report: _ensure_source_files_in_phases

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If required_source_files is None or empty, returns
    {"forced": [], "augmented": {}, "augmented_modules": []}
    without modifying the file at phases_json
  - If required_source_files is non-empty:
    (a) Every path in required_source_files not already present in any
        source_files list in phases_json (after normalizing "\" to "/" in
        both the existing entries and the required files) is appended, in
        its original form, to the source_files list of the first module of
        the phase with the smallest "phase" number
    (b) If no phase exists in phases_json, a single phase numbered 1
        containing one module named "entry_points" is created to receive
        all missing source files; the phase has an empty depends_on_phases
        list
    (c) If the earliest phase exists but has no modules, a module named
        "entry_points" with an empty source_files list is created to
        receive the missing source files
    (d) The description of the receiving module is appended with a note
        listing the missing file paths; descriptions are merged without
        duplication (i.e., if the new note is already a substring of the
        existing description, no change is made)
    (e) The file at phases_json is atomically overwritten with the updated
        JSON, indented with 2 spaces
    (f) Returns a dict with exactly three keys:
        - "forced": list of paths (in the same order as they appear in
          required_source_files) that were not already present and were
          therefore added
        - "augmented": dict mapping the source phase number (an integer,
          as it was when the file was opened, prior to any renumbering) to
          the list of added paths
        - "augmented_modules": list of dicts, each containing "phase"
          (int), "module" (str), and "added_files" (list of str),
          identifying which specific module received the missing files

---

### Actual Behavior

If `required_source_files` is None or empty, the file `phases_json` is unchanged and the function returns `{"forced": [], "augmented": {}, "augmented_modules": []}`. Otherwise, let `norm_paths_required` = { normalize_path(p) for p in required_source_files } where normalize_path replaces backslashes with forward slashes. Let `existing_norm_paths` = set of all normalized source file paths across all modules in all phases in the original file. If norm_paths_required ⊆ existing_norm_paths, the file is unchanged and the function returns the empty result. Otherwise, let `missing` = [p for p in required_source_files if normalize_path(p) ∉ existing_norm_paths] (preserving order). Then the function modifies the file as follows: (1) If the original file had no `phases` key or an empty list, a new phase object is created with `phase: 1`, `name: "Entry Points"`, `description: "Entry-point source files."`, and empty `modules` list, and becomes the only phase. Otherwise, select the phase with the minimum `phase` numeric value from the existing phases (call it `target_phase`). (2) If target_phase has no modules, a new module with `name: "entry_points"`, `description: ""`, and `source_files: []` is added. (3) The first module in `target_phase.modules` (index 0) has all elements of `missing` appended to its `source_files` list, and its `description` is updated by joining with the note "Includes required entry-point source file(s): <comma-separated missing>." via `_merge_descriptions` (which appends the note if not already present). (4) The modified data is written back to the file, overwriting its content. The final file remains valid JSON conforming to the phases.json schema. The function returns a dictionary `result` where `result.forced` is `missing`, `result.augmented` is a dict mapping `target_phase.phase` to a copy of `missing`, and `result.augmented_modules` is a list with one dict `{phase: target_phase.phase, module: target_phase.modules[0].name, added_files: copy of missing}`.

---

## Code Evidence

Line 27: missing = [sf for sf in required_source_files if sf.replace("\\", "/") not in listed]; Line 51: module.setdefault("source_files", []).extend(missing)

---

## Trigger Condition

The code does not deduplicate entries in required_source_files that normalize to the same path, so a path appearing multiple times may be appended multiple times to the module's source_files list. This results in a file that contains duplicate paths, violating the specification requirement that no path already present in phases_json (after '/' normalization) is duplicated.

---

## How to trigger the bug

When `required_source_files` contains two (or more) entries that normalize to the same path (e.g. `'path/to/dup.py'` and `'path\to\dup.py'`), the list comprehension on line 762 computes `missing` by checking each entry against the original `listed` set — it does not deduplicate within `required_source_files` itself. Both entries pass the check (since neither normalized form was already present in `phases_json`) and are appended to the module's `source_files` list, resulting in duplicated paths.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | Path to a temporary `phases.json` containing one phase (number 1) with one module (`"test_module"`) owning `["existing_file.py"]` |
| `required_source_files` | `["path/to/dup.py", "path\\to\\dup.py"]` |

### Expected (spec-correct) Output

`source_files` should be `["existing_file.py", "path/to/dup.py"]` — only one copy of the normalized path added. `forced` should be `["path/to/dup.py"]`.

### Actual (buggy) Output

`source_files` = `["existing_file.py", "path/to/dup.py", "path\\to\\dup.py"]` — both entries were appended. `forced` = `["path/to/dup.py", "path\\to\\dup.py"]` — both entries recorded in the return value.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, json, os, tempfile
sys.path.insert(0, os.getcwd())

from src.pipeline_setup import _ensure_source_files_in_phases

tmpdir = tempfile.mkdtemp()
phases_json = os.path.join(tmpdir, "phases.json")

initial_data = {
    "phases": [{
        "phase": 1,
        "name": "Test Phase",
        "modules": [{
            "name": "test_module",
            "source_files": ["existing_file.py"]
        }]
    }]
}
with open(phases_json, "w") as f:
    json.dump(initial_data, f)

result = _ensure_source_files_in_phases(
    phases_json,
    ["path/to/dup.py", "path\\to\\dup.py"]
)

with open(phases_json) as f:
    data = json.load(f)

print("source_files:", data["phases"][0]["modules"][0]["source_files"])
# actual (buggy) output: ['existing_file.py', 'path/to/dup.py', 'path\\to\\dup.py']
# expected (correct) output: ['existing_file.py', 'path/to/dup.py']
```

---

## Probe Script

```python
import sys
import json
import os
import tempfile

# Add the repo root to sys.path so 'src' is importable
# Script is at fm_agent/bug_validation/probe_*.py, go up 3 levels to repo root
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _ensure_source_files_in_phases
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary phases.json with one phase and one module
tmpdir = tempfile.mkdtemp()
phases_json = os.path.join(tmpdir, "phases.json")

initial_data = {
    "phases": [
        {
            "phase": 1,
            "name": "Test Phase",
            "description": "A test phase.",
            "depends_on_phases": [],
            "modules": [
                {
                    "name": "test_module",
                    "description": "Test module.",
                    "source_files": ["existing_file.py"]
                }
            ]
        }
    ]
}

with open(phases_json, "w") as f:
    json.dump(initial_data, f, indent=2)

# required_source_files with two entries that normalize to the same path
# 'path/to/dup.py' and 'path\to\dup.py' both normalize to 'path/to/dup.py'
required_source_files = ["path/to/dup.py", "path\\to\\dup.py"]

result = _ensure_source_files_in_phases(phases_json, required_source_files)

# Read back the modified phases.json
with open(phases_json, "r") as f:
    modified_data = json.load(f)

# Get the source_files of the first module of the first phase
actual_source_files = modified_data["phases"][0]["modules"][0]["source_files"]
actual_forced = result["forced"]

# Expected (spec-correct): only ONE copy of the normalized path should be added
expected_source_files = ["existing_file.py", "path/to/dup.py"]
expected_forced = ["path/to/dup.py"]

# Check: are there duplicates in the source_files list?
normalized_added = [sf.replace("\\", "/") for sf in actual_source_files]
duplicates_detected = len(normalized_added) != len(set(normalized_added))

# The bug is: both entries end up in source_files and forced
passed = duplicates_detected or len(actual_forced) > 1

# Clean up
os.remove(phases_json)
os.rmdir(tmpdir)

if passed:
    print(f"CONFIRMED — actual source_files: {actual_source_files!r} | expected: {expected_source_files!r}")
    print(f"  forced: {actual_forced!r} (expected max 1 entry)")
else:
    print(f"NOT CONFIRMED — actual matched expected: source_files={actual_source_files!r}, forced={actual_forced!r}")
```

### Probe Output

```
CONFIRMED — actual source_files: ['existing_file.py', 'path/to/dup.py', 'path\\to\\dup.py'] | expected: ['existing_file.py', 'path/to/dup.py']
  forced: ['path/to/dup.py', 'path\\to\\dup.py'] (expected max 1 entry)
```
