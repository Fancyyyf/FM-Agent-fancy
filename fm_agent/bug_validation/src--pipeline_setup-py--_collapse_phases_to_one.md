# Bug Report: _collapse_phases_to_one

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When phases.json contains no phases (empty "phases" array), the
    function returns immediately; no files are modified or created.
  - Otherwise, phases.json is replaced: the "phases" array contains
    exactly one element  a phase with:
      * "phase" set to the integer 1.
      * "name" set to the string "Unified Analysis Phase".
      * "modules" being the concatenation of every module from every
        original phase, preserving the ascending phase-number order of
        original phases and the original module order within each phase.
      * "description" being the concatenation of every non-empty
        (after stripping whitespace) description from every original
        phase, each prefixed by "Phase {N} ({name}): " and joined by
        "\n\n". If no original phase had a non-empty description,
        "description" is the empty string.
      * "depends_on_phases" set to the empty list [].
  - Domain context files are merged:
      * Every existing phase_NN_types.txt file is read; their content
        is concatenated with "\n\n" separators and written to
        phase_01_types.txt under spec_prompts/domain_context/.
      * All other phase_*_types.txt files (matching the glob pattern)
        are deleted.
      * If no phase_NN_types.txt files existed, phase_01_types.txt is
        not created and no deletions occur.
  - Returns None.

---

### Actual Behavior

Upon successful execution: (1) if the initial 'phases' array in 'phases.json' was empty, the file system is unchanged and the function returns; (2) otherwise, 'phases.json' is overwritten with a single phase whose 'phase' equals that of the original first phase, 'name' = "Unified Analysis Phase", 'description' = the concatenation (separated by "\n\n") of non-empty original descriptions each prefixed with "Phase {phase} ({name}): ", 'modules' = the concatenation of all original phase modules, and 'depends_on_phases' = []. In the subdirectory 'spec_prompts/domain_context/', if any 'phase_NN_types.txt' files exist for the original phases, their (stripped) contents are concatenated (separator "\n\n") and written to 'phase_01_types.txt', and all other files matching the glob 'phase_*_types.txt' are deleted; if no such files exist, the directory is left unmodified. If an exception (I/O, JSON decode, etc.) occurs, the function terminates and the file system may be partially modified (state undefined).

---

## Code Evidence

Line 15: first["name"] = "Unified Analysis Phase"; Line 16: first["description"] = merged_description; Line 17-21: first["modules"] = [ ... ]; Line 22: first["depends_on_phases"] = []; (the code never sets first['phase'] = 1, leaving the original phase number unchanged)

---

## Trigger Condition

The specification explicitly requires the merged phase's 'phase' to be the integer 1, but the code preserves the 'phase' value from the first original phase. As a result, any nonempty input where the first original phase number is not 1 causes a violation of the specification.

---

## How to trigger the bug

A `phases.json` with multiple phases where the first phase has a number other than 1 is created. The function `_collapse_phases_to_one` is called, which overwrites `phases.json` with a single merged phase that retains the original phase number (e.g., 3) instead of setting it to 1 as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | A temporary directory containing `phases.json` with two phases: phase 3 (name="Phase Three", modules=["mod_a.py", "mod_b.py"]) and phase 5 (name="Phase Five", modules=["mod_c.py"]) |

### Expected (spec-correct) Output

`phases.json` with a single phase where `"phase": 1`

### Actual (buggy) Output

`phases.json` with a single phase where `"phase": 3` (the original first phase number)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.pipeline_setup import _collapse_phases_to_one
import tempfile, os, json

tmp_dir = tempfile.mkdtemp()
phases_json = {
    "phases": [
        {"phase": 3, "name": "P3", "description": "", "modules": ["a.py"]},
        {"phase": 5, "name": "P5", "description": "", "modules": ["b.py"]}
    ]
}
with open(os.path.join(tmp_dir, "phases.json"), "w") as f:
    json.dump(phases_json, f)

_collapse_phases_to_one(tmp_dir)

with open(os.path.join(tmp_dir, "phases.json")) as f:
    result = json.load(f)
print(result["phases"][0]["phase"])  # actual (buggy) output: 3
                                     # expected (correct) output: 1
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

try:
    from src.pipeline_setup import _collapse_phases_to_one
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Create a temporary work directory with phases.json where first phase number is NOT 1
tmp_dir = tempfile.mkdtemp(prefix="bug_probe_")

# phases.json with first phase number = 3 (not 1)
phases_json = {
    "phases": [
        {
            "phase": 3,
            "name": "Phase Three",
            "description": "Third phase description",
            "modules": ["mod_a.py", "mod_b.py"],
            "depends_on_phases": [1, 2]
        },
        {
            "phase": 5,
            "name": "Phase Five",
            "description": "Fifth phase description",
            "modules": ["mod_c.py"],
            "depends_on_phases": [3]
        }
    ]
}

phases_path = os.path.join(tmp_dir, "phases.json")
with open(phases_path, "w") as f:
    json.dump(phases_json, f, indent=2)

try:
    _collapse_phases_to_one(tmp_dir)

    # Read the resulting phases.json
    with open(phases_path) as f:
        result = json.load(f)

    merged_phase = result["phases"][0]
    actual_phase = merged_phase["phase"]

    # Spec says phase must be 1 — buggy code preserves original phase number
    expected_phase = 1

    if actual_phase != expected_phase:
        print(f'CONFIRMED — spec requires phase=1, but code returned phase={actual_phase}')
    else:
        print(f'NOT CONFIRMED — actual phase matched expected: {actual_phase}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Cleanup temp directory
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — spec requires phase=1, but code returned phase=3
```
