# Bug Report: _filter_phases_to_submodules

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When submodules is None or empty, phases.json is unchanged on disk and
    the function returns {"removed": 0, "modified_modules": []}.
  - When submodules is non-empty, every source_file path in every module of
    every phase is classified: paths that begin with any of the submodule
    directory names are retained; all other paths are removed from their
    module.
  - Returns a dict with two keys: "removed" maps to the total count (int) of
    removed source_file entries; "modified_modules" maps to a list of
    objects, one per module from which at least one file was removed, each
    containing the phase number, module name, the list of removed file paths,
    and the list of retained file paths.
  - When at least one source_file is removed, the file at phases_json is
    overwritten with the filtered phases.json content; when no source_file is
    removed, the file at phases_json is not modified.

---

### Actual Behavior

After successful execution (i.e., no unhandled I/O or JSON parse error), the function returns a dictionary with keys 'removed' (integer) and 'modified_modules' (list). If submodules is falsy (None or empty), the function returns {'removed': 0, 'modified_modules': []} without reading or modifying the file at phases_json. Otherwise: the file at phases_json is read into memory (old_data). The function iterates over the phases array sorted by the 'phase' key, and for each module it partitions its source_files list into kept (files whose path starts with any string in submodules) and removed (all others). If removed is empty, the module is unchanged. If removed is non-empty, the module's 'source_files' field is replaced with kept, the count is added to removed_total, and a record is appended to modified_modules containing 'phase' (the phase number), 'module' (the module's name, defaulting to ''), 'removed_files' (list of removed file strings), and 'source_files' (list of kept file strings). After processing all modules, if modified_modules is non-empty, the file at phases_json is overwritten with the updated JSON (indent=2); otherwise the file remains unchanged. The returned dictionary has 'removed' equal to removed_total and 'modified_modules' equal to the list of modification records, ordered by phase (ascending) and module iteration order.

---

## Code Evidence

Line 718: `"phase": phase.get("phase"),`

---

## Trigger Condition

Specification states that each modified module record must contain the phase number. When the phase object lacks a 'phase' key, phase.get("phase") returns None, which is not a number, violating the post-condition.

---

## How to trigger the bug

When a phases.json file contains a phase object that lacks the `"phase"` key (e.g., `{"name": "some_phase", "modules": [...]}`), calling `_filter_phases_to_submodules` with a non-empty `submodules` list that causes at least one source file to be removed will produce a `modified_modules` entry where `"phase"` is `None` instead of an integer. The specification requires the phase number to be present in every modified module record.

### Inputs

| Parameter    | Value                                                                      |
|-------------|----------------------------------------------------------------------------|
| `phases_json` | Path to a JSON file with `{"phases": [{"name": "...", "modules": [{"name": "m", "source_files": ["outside/file.py"]}]}]}` (no `"phase"` key) |
| `submodules`  | `["core"]` — a list that does not match any source file path, triggering removal |

### Expected (spec-correct) Output

A `modified_modules` entry with `"phase"` set to an integer (e.g., `0` if defaulted, or the actual phase number).

### Actual (buggy) Output

A `modified_modules` entry with `"phase": null` (Python `None`), which is not a number.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
from src.pipeline_setup import _filter_phases_to_submodules

phases = {"phases": [
    {"name": "missing_phase_key",
     "modules": [{"name": "test_module", "source_files": ["outside/file.py"]}]}
]}
tmpdir = tempfile.mkdtemp()
path = os.path.join(tmpdir, "phases.json")
with open(path, "w") as f:
    json.dump(phases, f)

result = _filter_phases_to_submodules(path, ["core"])
print(result["modified_modules"][0]["phase"])
# actual (buggy) output: None
# expected (correct) output: an integer
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile

try:
    from src.pipeline_setup import _filter_phases_to_submodules

    # Create a temporary phases.json with a phase that lacks a "phase" key.
    phases_content = {
        "phases": [
            {
                # Intentionally NO "phase" key here.
                "name": "missing_phase_key",
                "modules": [
                    {
                        "name": "test_module",
                        "source_files": ["outside_scope/file.py"]
                    }
                ]
            }
        ]
    }

    tmpdir = tempfile.mkdtemp()
    phases_path = os.path.join(tmpdir, "phases.json")
    with open(phases_path, "w") as f:
        json.dump(phases_content, f)

    # Call with a submodules list that does NOT match any source_file,
    # so files get removed and modified_modules is non-empty.
    result = _filter_phases_to_submodules(phases_path, ["core"])

    mods = result.get("modified_modules", [])
    if not mods:
        print("NOT CONFIRMED — no modules were modified; bug path not triggered")
        sys.exit(0)

    actual_phase = mods[0].get("phase")
    expected_phase_type = type(1)  # Should be int

    # Bug: phase.get("phase") returns None when the key is absent.
    if actual_phase is None:
        print(f"CONFIRMED — actual phase: {actual_phase!r} (None) | expected: an integer (int)")
    elif isinstance(actual_phase, int):
        print(f"NOT CONFIRMED — actual phase is int ({actual_phase!r}); no bug detected")
    else:
        print(f"NOT CONFIRMED — actual phase is {actual_phase!r} (type: {type(actual_phase).__name__}), not None")

    # Cleanup
    os.remove(phases_path)
    os.rmdir(tmpdir)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual phase: None (None) | expected: an integer (int)
```
