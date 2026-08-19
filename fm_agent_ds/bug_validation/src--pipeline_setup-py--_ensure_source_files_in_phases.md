# Bug Report: _ensure_source_files_in_phases

**Source file:** `src/pipeline_setup-py/_ensure_source_files_in_phases.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When required_source_files is None or empty, returns {'forced': [], 'augmented': {}, 'augmented_modules': []} without reading or modifying phases_json. Otherwise, guarantees that after return every path in required_source_files (with backslash directory separators normalized to forward slash) appears in the source_files list of exactly one module in the phases.json file. Returns a dict where: 'forced' is the list of required paths that were not already present in any phase module's source_files before the call (empty when all paths were already present); 'augmented' maps the numeric phase identifier of the receiving phase (the phase with the smallest phase number) to the list of paths added to it; 'augmented_modules' lists each module that received new files, each entry containing the module's phase number, module name, and the added file paths. If the phases.json file originally contained no phases, a single phase numbered 1 is created containing one module whose source_files list contains all paths from required_source_files. The receiving module's description field is extended to include a note referencing the added source files (without duplicating any description content already present). No existing phases are removed, no existing module loses any source files, and phase numbering of pre-existing phases is unchanged.

---

### Actual Behavior

If the function completes without raising an exception, the following holds:
Let F_before be the JSON contents of the file at phases_json before the call.
- If required_source_files is falsy (None or empty sequence): the function returns {'forced': [], 'augmented': {}, 'augmented_modules': []} and the file is unchanged (F_after = F_before).
- Otherwise, let required_norm = { p with backslashes replaced by forward slashes for p in required_source_files } and existing_norm = { p with backslashes replaced by forward slashes for p in all source_files listed in any module of any phase in F_before }.
  - If required_norm  existing_norm, the function returns the same empty dictionary and the file is unchanged.
  - Otherwise, missing = [ sf for sf in required_source_files if sf with backslashes replaced not in existing_norm ] (preserving order). The file is transformed: the earliest phase (by numeric 'phase' key) in F_before is selected; if no phases exist, a new phase with 'phase': 1, name 'Entry Points', description 'Entry-point source files.', empty modules, empty depends_on_phases is created. In that phase's 'modules' list, if empty, a new module with name 'entry_points', empty description, and empty source_files is appended. The first module in that list has its 'source_files' extended by appending all paths from missing (as given, without normalization) and its 'description' updated to _merge_descriptions(old_description, 'Includes required entry-point source file(s): ' + ', '.join(missing) + '.'). No other phases or modules are modified. The file at phases_json is overwritten with the resulting JSON object (F_after). The function returns:
  {'forced': missing,
   'augmented': {earliest_phase_number: list(missing)},
   'augmented_modules': [{'phase': earliest_phase_number, 'module': name_of_first_module, 'added_files': list(missing)}]}
  where earliest_phase_number is the 'phase' value of the selected earliest phase.

---

## Code Evidence

Line 27: missing = [sf for sf in required_source_files if sf.replace("\\", "/") not in listed]
Line 28: if not missing:
Line 29:     return {"forced": [], "augmented": {}, "augmented_modules": []}

---

## Trigger Condition

The specification guarantees that after return each required source file appears in exactly one module. When a required file already exists in multiple modules, the code does not detect or fix this duplication; it simply returns early without modification. This leaves the file in a state that violates the post-condition.

---

## How to trigger the bug

The bug is triggered when a required source file is already present in phases.json but appears in **more than one module**. The code builds a flat `set` of all source files across all phases/modules (normalizing backslashes) and only tests set membership. If the file is in the set at all — regardless of how many modules claim it — the function returns an empty result without removing the duplicate copies. The spec requires the file to be in **exactly one** module.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` (file contents) | A phases.json with one phase containing two modules, both listing `"foo.py"` in their `source_files` |
| `required_source_files` | `["foo.py"]` |

### Expected (spec-correct) Output

The function should detect that `foo.py` appears in multiple modules and either (a) remove it from all but one module so it appears in exactly one, or (b) at minimum not return an empty result, since the post-condition ("exactly one module") is violated.

### Actual (buggy) Output

```json
{"forced": [], "augmented": {}, "augmented_modules": []}
```

`foo.py` remains listed in both modules after the call — the duplicate is not detected or fixed.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os, sys
sys.path.insert(0, ".")
from src.pipeline_setup import _ensure_source_files_in_phases

tmpdir = tempfile.mkdtemp()
phases_json = f"{tmpdir}/phases.json"
with open(phases_json, "w") as f:
    json.dump({"phases": [{
        "phase": 1, "name": "Phase",
        "modules": [
            {"name": "mod_a", "source_files": ["foo.py"]},
            {"name": "mod_b", "source_files": ["foo.py"]},
        ]
    }]}, f)

result = _ensure_source_files_in_phases(phases_json, ["foo.py"])
# actual (buggy) output: {"forced": [], "augmented": {}, "augmented_modules": []}
# expected (correct) output: function should detect/fix duplication so foo.py is in exactly 1 module
```

---

## Probe Script

```py
import sys
import os
import json
import tempfile

# Add repo root to sys.path so the 'src' package + 'config' module resolve.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _ensure_source_files_in_phases
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Build a temporary phases.json where "foo.py" is duplicated across TWO modules
# of the same phase.  The spec post-condition requires every required source
# file to appear in EXACTLY ONE module, but the implementation collects all
# source files into a flat set and only checks membership, not uniqueness.
tmpdir = tempfile.mkdtemp()
phases_json_path = os.path.join(tmpdir, "phases.json")

initial_phases = {
    "phases": [
        {
            "phase": 1,
            "name": "Phase One",
            "description": "First phase.",
            "modules": [
                {
                    "name": "mod_a",
                    "description": "Module A.",
                    "source_files": ["foo.py", "bar.py"],
                },
                {
                    "name": "mod_b",
                    "description": "Module B.",
                    "source_files": ["foo.py", "baz.py"],
                },
            ],
            "depends_on_phases": [],
        }
    ]
}
with open(phases_json_path, "w") as f:
    json.dump(initial_phases, f)

required_source_files = ["foo.py"]

try:
    result = _ensure_source_files_in_phases(phases_json_path, required_source_files)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Re-read phases.json to count how many modules still claim "foo.py".
with open(phases_json_path, "r") as f:
    after = json.load(f)

foo_count = 0
for phase in after["phases"]:
    for module in phase["modules"]:
        if "foo.py" in module.get("source_files", []):
            foo_count += 1

# Bug reproduced when:
#   1) The function returned an empty result (did NOT add or fix anything), AND
#   2) foo.py still appears in more than 1 module.
# The spec requires exactly 1.
forced_empty = result.get("forced") == []
aug_empty = result.get("augmented") == {}
still_duplicated = foo_count > 1

bug_confirmed = forced_empty and aug_empty and still_duplicated

if bug_confirmed:
    print(
        f'CONFIRMED — actual: forced={result["forced"]!r}, foo.py appears in '
        f'{foo_count} modules after call | expected (spec): exactly 1 module'
    )
else:
    print(
        f'NOT CONFIRMED — result={result!r}, foo_count={foo_count}'
    )

# Cleanup temporary directory.
import shutil
shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — actual: forced=[], foo.py appears in 2 modules after call | expected (spec): exactly 1 module
```
