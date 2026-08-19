# Bug Report: _build_module_description_prompt

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns None if every module identified in modified_modules has no source files in phases_json  either the module is not found or its 'source_files' list is empty. Otherwise, returns a non-empty string that is a complete natural-language prompt. The returned prompt identifies every module in modified_modules that owns at least one source file by its phase number and module name exactly as they appear in phases_json, and instructs the recipient to rewrite the 'description' field of each identified module to accurately describe the module's current 'source_files' entries. The prompt forbids any modification to other fields ('source_files', 'phase', 'name', 'depends_on_phases'), modules not enumerated, the overall phase structure, and any project source file; it also requires the JSON to remain valid after the edit. The function performs no modification to phases_json itself.

---

### Actual Behavior

Natural language: After the function executes, the file `phases_json` is unchanged. The function returns `None` if and only if no entry in `modified_modules` corresponds to a module in the JSON that has a non-empty `source_files` list; otherwise, it returns a non-empty string. The string begins with the literal text "Here is a list of modules in fm_agent/phases.json:\n\n", followed by one line per qualifying module in the order they appear in `modified_modules`. Each line is formatted as "  - phase {phase} module \"{module}\"", where {phase} is the integer phase and {module} is the module name, with the module name enclosed in escaped double-quotes (backslash then double quote). After the list of modules, the string continues with the literal text "\n\nPlease update the \"description\" field of each module above so that it accurately describes the source files it now owns.\nRules:\n- Edit ONLY the \"description\" field of the listed modules in fm_agent/phases.json.\n- Do NOT change any \"source_files\", \"phase\", \"name\", \"depends_on_phases\", or the phase structure in any way.\n- Do NOT touch modules that are not in the list above.\n- Keep the JSON valid.\n- Do NOT modify any project source file; only edit fm_agent/phases.json.".

Formal: Let `data = json.load(open(phases_json))` (guaranteed by pre-condition). Define `SF = {(p['phase'], m['name']): list(m['source_files']) for p in data['phases'] for m in p['modules']}`. Define `Q = [m for m in modified_modules if (m['phase'], m['module']) in SF and SF[(m['phase'], m['module'])] != []]`. Then the return value `R` is `None` if `Q` is empty, else `R = "Here is a list of modules in fm_agent/phases.json:\n\n" + "\n".join("  - phase {} module \"{}\"".format(m['phase'], m['module']) for m in Q) + "\n\nPlease update the \"description\" field of each module above so that it accurately describes the source files it now owns.\nRules:...` (the instructions as above).

---

## Code Evidence

Line 17: source_files_by_key[(phase.get("phase"), module.get("name", ""))] = list(
Line 18: module.get("source_files", [])
Line 19: )
Line 22: if not source_files_by_key.get((m["phase"], m["module"])):

---

## Trigger Condition

The dictionary source_files_by_key uses (phase, module name) as key, which is not guaranteed unique. Duplicate modules in the same phase cause earlier entries with source files to be overwritten by later ones without. In the counterexample, the first 'A' module with source files is replaced by the second empty one, causing the module to be considered as having no source files, so None is returned. Specification requires listing modules that own source files, but the code misses the one with files due to overwrite.

---

## How to trigger the bug

When `phases.json` contains duplicate entries for the same module within a phase — where the first entry has a non-empty `source_files` list and the second has an empty one — the dictionary `source_files_by_key` overwrites the first entry's value with the empty list from the second. The lookup at line 24 then finds the empty list, skips the module, and the function returns `None` instead of a prompt listing the module.

### Inputs

| Parameter | Value |
|-----------|-------|
| phases_json | A JSON file containing a phase with two modules both named "A": first has `source_files: ["src/core.py"]`, second has `source_files: []` |
| modified_modules | `[{"phase": 1, "module": "A"}]` |

### Expected (spec-correct) Output

A non-empty prompt string containing the line `"  - phase 1 module \"A\""` followed by the standard update-instruction text.

### Actual (buggy) Output

`None`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, json, os, tempfile
sys.path.insert(0, os.getcwd())
from src.pipeline_setup import _build_module_description_prompt

with tempfile.TemporaryDirectory() as tmpdir:
    phases_path = os.path.join(tmpdir, "phases.json")
    phases_data = {
        "phases": [{
            "phase": 1,
            "modules": [
                {"name": "A", "source_files": ["src/core.py"], "description": "Module A"},
                {"name": "A", "source_files": [], "description": "Duplicate empty"},
            ]
        }]
    }
    with open(phases_path, "w") as f:
        json.dump(phases_data, f)

    result = _build_module_description_prompt(
        [{"phase": 1, "module": "A"}], phases_path
    )
    print(result)
# actual (buggy) output: None
# expected (correct) output: A non-empty prompt string listing phase 1 module "A"
```

---

## Probe Script

```python
"""Probe script for bug: _build_module_description_prompt dict key collision
causes modules with source files to be treated as empty when duplicate module
names exist in the same phase.
"""

import sys
import json
import os
import tempfile

try:
    from src.pipeline_setup import _build_module_description_prompt

    with tempfile.TemporaryDirectory() as tmpdir:
        phases_path = os.path.join(tmpdir, "phases.json")

        # phases.json with duplicate modules in the same phase.
        # First "A" has source files; second "A" has no source files.
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "modules": [
                        {
                            "name": "A",
                            "source_files": ["src/core.py"],
                            "description": "Core module",
                        },
                        {
                            "name": "A",
                            "source_files": [],
                            "description": "Duplicate empty",
                        },
                    ]
                }
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f)

        # modified_modules points to module "A" in phase 1
        modified_modules = [{"phase": 1, "module": "A"}]

        actual = _build_module_description_prompt(modified_modules, phases_path)

        # Spec: since module "A" in phase 1 has source_files ["src/core.py"],
        # the function should return a non-empty prompt listing that module.
        # Bug: returns None because dict overwrite replaces the first entry
        # (with source_files) with the second (empty).
        expected_is_none = False  # spec requires non-None prompt
        bug_hit = actual is None and expected_is_none is False

        if bug_hit:
            print(
                "CONFIRMED — actual: None | expected: non-empty prompt string "
                "listing phase 1 module A"
            )
        else:
            print(
                "NOT CONFIRMED — actual matched expected: "
                f"{actual!r}"
            )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: None | expected: non-empty prompt string listing phase 1 module A
```
