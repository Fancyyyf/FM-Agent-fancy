# Bug Report: _deduplicate_phases

**Source file:** `src/pipeline_setup.py`
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

After successful execution (no exceptions), the following holds:

Natural language:
The file at `phases_path = os.path.join(phases_dir, "phases.json")` is overwritten with a JSON object `new_data` that preserves the original phases and modules structure (same order, same counts, same names) but with each module's `source_files` list deduplicated so that every source file appears at most once overall. For each source file that appeared in the original `old_data`, it is kept only in the module that first claims it according to ascending phase number (ties broken by original stable order among phases with equal numbers) and then by original module order within that phase; later occurrences are removed. Modules that lose all files are retained without dropping phases or renumbering. Within each module, the relative order of retained files matches their original order. The function returns a dictionary `result` with key `"modified_modules"`, whose value is a list of objects, one per module whose `source_files` list changed. Each object contains the phase number (`"phase"`), module name (`"module"`), the list of removed files in original order (`"removed_files"`), and the new deduplicated list (`"source_files"`). Log messages are emitted for each removed duplicate file.

---

## Code Evidence

Line 22-30: the deduplication loop that removes any source file already in the global `seen` set, which incorrectly removes duplicate files within the same module.

---

## Trigger Condition

The specification requires deduplication only for files appearing in multiple modules. In this input, 'a.py' appears twice in the same module, not in multiple modules. The code removes the second occurrence, changing the module's source_files and reporting it as modified, whereas the specification expects the file list to remain unchanged and 'modified_modules' to be empty.

---

## How to trigger the bug

The bug is triggered when a module's `source_files` list contains the same file path more than once. The global `seen` set (`seen = set()` on line 71) tracks all file paths encountered across all phases and modules. When the same file appears twice within a single module, the second occurrence is already in `seen`, so the deduplication loop removes it — but the specification requires deduplication only across *different* modules, not within the same module.

### Inputs

| Parameter | Value |
|-----------|-------|
| phases_dir | (temp directory containing phases.json) |
| phases.json → phases[0].modules[0].source_files | `["a.py", "b.py", "a.py"]` |

### Expected (spec-correct) Output

`["a.py", "b.py", "a.py"]` — source_files unchanged, `modified_modules` is `[]`

### Actual (buggy) Output

`["a.py", "b.py"]` — the second occurrence of `a.py` was incorrectly removed

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.pipeline_setup import _deduplicate_phases

with tempfile.TemporaryDirectory() as tmpdir:
    phases_json = os.path.join(tmpdir, "phases.json")
    data = {
        "phases": [{
            "phase": 1,
            "modules": [{
                "name": "module_foo",
                "source_files": ["a.py", "b.py", "a.py"]
            }]
        }]
    }
    with open(phases_json, "w") as f:
        json.dump(data, f)

    result = _deduplicate_phases(tmpdir)

    with open(phases_json, "r") as f:
        out = json.load(f)
    print(out["phases"][0]["modules"][0]["source_files"])
    # actual (buggy) output: ['a.py', 'b.py']
    # expected (correct) output: ['a.py', 'b.py', 'a.py']
```

---

## Probe Script

```python
"""Probe script for bug: _deduplicate_phases incorrectly deduplicates
files within the same module.

The spec: deduplication should only remove files that appear in MULTIPLE
modules. Within a single module, duplicate entries should be preserved.

The bug: the global `seen` set tracks ALL seen files, so if a file appears
twice in the same module's source_files, the second occurrence gets removed.
"""
import sys
import os
import json
import tempfile

# Import via the public entry point (src package)
from src.pipeline_setup import _deduplicate_phases

def test():
    # Create a temp directory with a phases.json containing a module
    # that lists the same source file twice in its source_files list.
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_json_path = os.path.join(tmpdir, "phases.json")

        # Input: one phase, one module, "a.py" appears TWICE in source_files
        input_data = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [
                        {
                            "name": "module_foo",
                            "source_files": ["a.py", "b.py", "a.py"]
                        }
                    ]
                }
            ]
        }

        with open(phases_json_path, "w") as f:
            json.dump(input_data, f)

        # Call the function under test
        result = _deduplicate_phases(tmpdir)

        # Read back the modified phases.json
        with open(phases_json_path, "r") as f:
            output_data = json.load(f)

        output_files = output_data["phases"][0]["modules"][0]["source_files"]

        # Spec says: dedup only across modules, not within the same module.
        # "a.py" appears twice in ONE module → should be preserved (both copies).
        # Expected: ["a.py", "b.py", "a.py"] — unchanged
        # Actual (buggy): ["a.py", "b.py"] — second "a.py" removed
        expected = ["a.py", "b.py", "a.py"]
        actual = output_files

        # The bug is confirmed if actual != expected
        if actual != expected:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
            print(f"modified_modules: {result.get('modified_modules')!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

if __name__ == "__main__":
    try:
        test()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: ['a.py', 'b.py'] | expected: ['a.py', 'b.py', 'a.py']
modified_modules: []
```
