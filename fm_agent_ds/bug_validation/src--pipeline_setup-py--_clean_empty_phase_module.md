# Bug Report: _clean_empty_phase_module

**Source file:** `src/pipeline_setup-py/_clean_empty_phase_module.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict with keys 'removed_phases' and 'renumbered'. 'removed_phases' is a list of phase numbers for phases that were removed. 'renumbered' is a dict mapping each original phase number to its final phase number, where an unchanged phase maps to itself. After return, phases.json under work_dir reflects these guarantees: every module in every phase has at least one source file, every phase has at least one module, phase numbers are contiguous integers starting from 1 preserving original ordering, and each phase's depends_on_phases contains only valid phase numbers that exist in the rewritten file. Domain-context types files at work_dir/spec_prompts/domain_context/ are synchronized with the new phase numbering.

---

### Actual Behavior

After normal termination, the file `work_dir/phases.json` contains a JSON object whose `"phases"` array is exactly the result of filtering the original sorted phases: a phase is kept iff after removing modules with falsy `source_files` (e.g., `None` or empty list) it still has at least one module; kept modules within a phase are only those with truthy `source_files`. The kept phases appear in their original relative order and are renumbered sequentially from 1. For each kept phase, if it had a `depends_on_phases` list, it is replaced by the sorted set of `renumbered[d]` for each `d` in the original list that is present in `renumbered`. The domaincontext files under `work_dir/spec_prompts/domain_context/` are updated: for each `n` in `removed_phases` the file `phase_{n}_types.txt` is deleted; for each `(old, new)` in `renumbered` with `old != new`, file `phase_{old}_types.txt` is renamed to `phase_{new}_types.txt`. The return value is a dictionary `{'removed_phases': removed_phases, 'renumbered': renumbered}`, where `removed_phases` is the list of original phase numbers of entirely removed phases, and `renumbered` is a dict mapping every kept phase's original phase number (if not `None`) to its new number, including identity mappings. If an exception occurs, the function does not return and the file system state is unspecified.

---

## Code Evidence

Line 18:     original_phases = sorted(data.get("phases", []), key=lambda p: p.get("phase", 0))

---

## Trigger Condition

The code sorts phases by their phase number, changing the original order of phases as they appear in the JSON array. The specification requires preserving the original ordering. With the given input, the code outputs phases renumbered as [1 (was 1), 2 (was 2)], but the correct behavior would keep the original order [2, 1] and renumber them to [1 (was 2), 2 (was 1)]. This violates the ordering guarantee.

---

## How to trigger the bug

The function `_clean_empty_phase_module` reads `phases.json` and sorts the phases by their `phase` number. If the phases in the JSON array already appear in a different order (e.g., phase 2 listed before phase 1), the `sorted()` call reorders them, destroying the original relative ordering. The specification explicitly requires "preserving original ordering."

### Inputs

| Parameter | Value |
|-----------|-------|
| work_dir | A temporary directory containing `phases.json` with phases in non-sequential array order: `[{"phase": 2, "name": "Phase Two", ...}, {"phase": 1, "name": "Phase One", ...}]` |

### Expected (spec-correct) Output

The original array order [Phase Two (phase=2), Phase One (phase=1)] is preserved. After renumbering from 1:
- First phase: phase=1, name="Phase Two" (was phase 2)
- Second phase: phase=2, name="Phase One" (was phase 1)
- `renumbered`: {2: 1, 1: 2}

### Actual (buggy) Output

The `sorted()` call reorders phases to [Phase One (phase=1), Phase Two (phase=2)]. After renumbering:
- First phase: phase=1, name="Phase One" (was phase 1)
- Second phase: phase=2, name="Phase Two" (was phase 2)
- `renumbered`: {1: 1, 2: 2} — both phases map to themselves, losing the original ordering information

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json
import os
import tempfile
import sys

_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.pipeline_setup import _clean_empty_phase_module

with tempfile.TemporaryDirectory() as work_dir:
    phases_json = {
        "phases": [
            {
                "phase": 2,
                "name": "Phase Two",
                "modules": [{"name": "m2", "source_files": ["b.py"]}],
                "depends_on_phases": [1]
            },
            {
                "phase": 1,
                "name": "Phase One",
                "modules": [{"name": "m1", "source_files": ["a.py"]}],
                "depends_on_phases": []
            }
        ]
    }
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump(phases_json, f)
    result = _clean_empty_phase_module(work_dir)
    with open(os.path.join(work_dir, "phases.json"), "r") as f:
        output = json.load(f)
    print("Phase order:", [p["name"] for p in output["phases"]])
    print("renumbered:", result["renumbered"])
    # actual (buggy) output: Phase order: ['Phase One', 'Phase Two'], renumbered: {1: 1, 2: 2}
    # expected (correct) output: Phase order: ['Phase Two', 'Phase One'], renumbered: {2: 1, 1: 2}
```

---

## Probe Script

```python
"""Probe for _clean_empty_phase_module bug: sorted() reorders phases by phase number,
violating the spec's "preserving original ordering" guarantee.

Trigger condition: phases.json has phases in an order different from their phase numbers.
The code sorts by phase number, changing the original array order.
"""
import sys
import os
import json
import shutil

# Ensure the repo root is on sys.path so that 'src' and top-level modules
# (e.g. 'config') are importable. The probe is run from the repo root, but
# sys.path[0] points to the script directory, not the cwd.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

try:
    from src.pipeline_setup import _clean_empty_phase_module

    # Create a fresh temporary directory as the probe workspace
    work_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_tmp_probe_clean_empty_phase")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    # phases.json with phases in NON-SEQUENTIAL order:
    # phase 2 appears FIRST, phase 1 appears SECOND
    original_phases_json = {
        "phases": [
            {
                "phase": 2,
                "name": "Phase Two",
                "description": "This is phase two, listed first in the array",
                "modules": [
                    {"name": "module_b", "description": "Module B", "source_files": ["b.py"]}
                ],
                "depends_on_phases": [1]
            },
            {
                "phase": 1,
                "name": "Phase One",
                "description": "This is phase one, listed second in the array",
                "modules": [
                    {"name": "module_a", "description": "Module A", "source_files": ["a.py"]}
                ],
                "depends_on_phases": []
            }
        ]
    }
    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path, "w") as f:
        json.dump(original_phases_json, f, indent=2)

    # Call the function
    result = _clean_empty_phase_module(work_dir)

    # Read back the output
    with open(phases_path, "r") as f:
        output_data = json.load(f)

    output_phases = output_data["phases"]

    # --- Assertions ---

    # The spec says original ordering should be preserved.
    # The original array order was [Phase Two (phase=2), Phase One (phase=1)].
    # After renumbering, if ordering is preserved:
    #   - First phase (was Phase Two, phase=2) -> new phase=1, name="Phase Two"
    #   - Second phase (was Phase One, phase=1) -> new phase=2, name="Phase One"
    # If ordering is NOT preserved (the bug), the sorted order produces:
    #   - First phase (was Phase One, phase=1) -> new phase=1, name="Phase One"
    #   - Second phase (was Phase Two, phase=2) -> new phase=2, name="Phase Two"

    first_phase = output_phases[0]
    second_phase = output_phases[1]

    # Verify the first phase in output should be "Phase Two" (original position 0)
    # If the bug is present, sorted() would put Phase One first
    expected_first_name = "Phase Two"  # Preserved ordering
    expected_second_name = "Phase One"

    actual_first_name = first_phase["name"]
    actual_second_name = second_phase["name"]

    # Verify phase numbering
    first_phase_num = first_phase["phase"]
    second_phase_num = second_phase["phase"]

    # Verify return value
    removed_phases = result["removed_phases"]
    renumbered = result["renumbered"]

    # The bug: sorted() reorders phases, so Phase One ends up first.
    # With the bug: first phase is "Phase One", second is "Phase Two".
    # Correct behavior: first phase is "Phase Two", second is "Phase One".
    ordering_preserved = (
        actual_first_name == expected_first_name
        and actual_second_name == expected_second_name
    )

    bug_confirmed = not ordering_preserved

    if bug_confirmed:
        print(
            f"CONFIRMED — ordering violated: first phase is '{actual_first_name}' "
            f"(expected '{expected_first_name}'), second is '{actual_second_name}' "
            f"(expected '{expected_second_name}') | "
            f"phase numbers: [{first_phase_num}, {second_phase_num}] | "
            f"renumbered: {renumbered} | removed_phases: {removed_phases}"
        )
    else:
        print(
            f"NOT CONFIRMED — ordering preserved: first phase is '{actual_first_name}' "
            f"as expected, second is '{actual_second_name}' as expected | "
            f"phase numbers: [{first_phase_num}, {second_phase_num}] | "
            f"renumbered: {renumbered} | removed_phases: {removed_phases}"
        )

    # Cleanup
    shutil.rmtree(work_dir)

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — ordering violated: first phase is 'Phase One' (expected 'Phase Two'), second is 'Phase Two' (expected 'Phase One') | phase numbers: [1, 2] | renumbered: {1: 1, 2: 2} | removed_phases: []
```
