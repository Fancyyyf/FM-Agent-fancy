# Bug Report: _clean_empty_phase_module

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- phases.json is modified in-place (file overwritten):
      * Every module whose source_files array is absent, null, or empty
        is removed from its phase.
      * Every phase left with no modules (empty modules array after
        pruning) is removed from the phases array.
      * Surviving phases are renumbered to a contiguous 1..N range
        in ascending order of their original phase numbers (no gaps).
      * For each surviving phase, every element in depends_on_phases
        is remapped to the new phase number; references to removed
        phases are dropped. The resulting depends_on_phases array is
        sorted in ascending order and contains no duplicates.
  - Domain context files are synced:
      * For every removed phase number, the corresponding
        phase_NN_types.txt file is deleted.
      * For every phase that was renumbered (old != new), the
        corresponding types file is renamed from phase_<old>_types.txt
        to phase_<new>_types.txt.
  - Returns a dict with two keys:
      * "removed_phases": list of int, the original phase numbers that
        were removed (empty list if none were removed).
      * "renumbered": dict mapping int (old phase number) to int (new
        phase number) for every phase present in the original
        phases.json, including phases whose number did not change
        (mapped to themselves).
  - If no phases were removed and no phase numbers changed, the return
    dict has "removed_phases": [] and "renumbered" where every key
    equals its value.

---

### Actual Behavior

On successful execution: The file 'phases.json' in `work_dir` is updated so that its 'phases' array contains exactly the phases from the original array that, after filtering each phase's modules to those with a truthy 'source_files' field, still have at least one module. The surviving phases are renumbered consecutively from 1 upwards, preserving the original ordering (by original 'phase' number). For each surviving phase, its 'depends_on_phases' list is replaced by a sorted list of the new numbers of its original dependencies that are still present; references to removed phases are dropped. If a phase originally had no 'depends_on_phases' field or it was null/falsy, it is left as is. The function also synchronises domain context files: for each removed phase number, the file `spec_prompts/domain_context/phase_<N>_types.txt` is deleted if it existed; for each mapping (old, new) in the renumbering where old ≠ new, the file `spec_prompts/domain_context/phase_<old>_types.txt` is renamed to `phase_<new>_types.txt`. The return value is a dictionary {'removed_phases': <list of removed original phase numbers>, 'renumbered': <dict mapping each original surviving phase number to its new number (if the number did not change it maps to itself)>}.

---

## Code Evidence

Line 36: renumbered = {}
Line 37: for new_num, phase in enumerate(kept, start=1):
Line 38: old_num = phase.get("phase")
Line 39: if old_num is not None:
Line 40: renumbered[old_num] = new_num
Line 41: phase["phase"] = new_num
Line 55: return {"removed_phases": removed_phase_nums, "renumbered": renumbered}

---

## Trigger Condition

The specification requires the 'renumbered' dict to map an old phase number to a new number "for every phase present in the original phases.json". This includes removed phases, but the code only adds entries for the surviving (kept) phases. In the counterexample, phase 1 is removed but appears in the original file; the code returns renumbered = {2: 1}, missing the required mapping for phase 1.

---

## How to trigger the bug

The `_clean_empty_phase_module` function processes `phases.json` to remove empty phases and renumber surviving ones. Its returned `renumbered` dict only contains entries for phases that survived the pruning — removed phases are omitted entirely, violating the spec which requires entries for ALL original phases.

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | temp directory containing `phases.json` with Phase 1 (empty, gets removed) and Phase 2 (non-empty, survives, renumbered to 1) |

### Expected (spec-correct) Output

The `renumbered` dict should contain an entry for Phase 1 (the removed phase): `{1: <some_value>, 2: 1}`

### Actual (buggy) Output

The `renumbered` dict only contains surviving phases: `{2: 1}` — Phase 1 is missing.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.pipeline_setup import _clean_empty_phase_module
import tempfile, json, os

phases_data = {
    "phases": [
        {"phase": 1, "name": "Empty", "modules": [{"name": "m", "source_files": []}], "depends_on_phases": []},
        {"phase": 2, "name": "Surviving", "modules": [{"name": "m", "source_files": ["src/main.py"]}], "depends_on_phases": [1]},
    ]
}
with tempfile.TemporaryDirectory() as wd:
    with open(os.path.join(wd, "phases.json"), "w") as f:
        json.dump(phases_data, f)
    result = _clean_empty_phase_module(wd)
    # actual (buggy) output:  renumbered = {2: 1}  (Phase 1 missing)
    # expected (correct) output: renumbered includes Phase 1
    print(result["renumbered"])  # {2: 1}
```

---

## Probe Script

```python
"""Probe script for bug: src--pipeline_setup-py--_clean_empty_phase_module

Spec claim: renumbered dict must contain entries for ALL phases in original
phases.json, including removed phases. The code only includes surviving phases.
"""

import sys
import os
import json
import tempfile

# Ensure the repo root is on sys.path for imports
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from src.pipeline_setup import _clean_empty_phase_module
except Exception as e:
    print(f"ERROR: Failed to import _clean_empty_phase_module: {e}")
    sys.exit(1)


def main():
    # Build a phases.json where phase 1 has NO source_files (will be removed)
    # and phase 2 has source_files (will survive, renumbered to 1).
    phases_data = {
        "phases": [
            {
                "phase": 1,
                "name": "Empty Phase",
                "description": "This phase has empty modules and should be removed.",
                "modules": [
                    {
                        "name": "empty_module",
                        "description": "",
                        "source_files": []  # empty → module removed → phase removed
                    }
                ],
                "depends_on_phases": []
            },
            {
                "phase": 2,
                "name": "Surviving Phase",
                "description": "This phase has source files and should survive, renumbered to 1.",
                "modules": [
                    {
                        "name": "real_module",
                        "description": "",
                        "source_files": ["src/main.py"]  # non-empty → module kept → phase kept
                    }
                ],
                "depends_on_phases": [1]  # depends on phase 1 which will be removed
            }
        ]
    }

    with tempfile.TemporaryDirectory() as work_dir:
        phases_path = os.path.join(work_dir, "phases.json")
        with open(phases_path, "w") as f:
            json.dump(phases_data, f, indent=2)

        result = _clean_empty_phase_module(work_dir)

        removed_phases = result.get("removed_phases", [])
        renumbered = result.get("renumbered", {})

        # Spec claim: renumbered must contain entries for EVERY phase in the
        # original phases.json, including removed phases.
        # Phase 1 was removed. If it is NOT in renumbered, the bug is CONFIRMED.
        removed_phase_num = 1
        expected_in_renumbered = removed_phase_num  # spec says ALL phases

        if removed_phase_num not in renumbered:
            print(
                f"CONFIRMED — Phase {removed_phase_num} was removed but is missing "
                f"from renumbered dict. "
                f"renumbered={renumbered}, removed_phases={removed_phases}"
            )
        else:
            print(
                f"NOT CONFIRMED — Phase {removed_phase_num} is present in renumbered "
                f"(value={renumbered[removed_phase_num]}). "
                f"renumbered={renumbered}, removed_phases={removed_phases}"
            )


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — Phase 1 was removed but is missing from renumbered dict. renumbered={2: 1}, removed_phases=[1]
```
