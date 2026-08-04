# Bug Report: _deduplicate_phases

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/pipeline_setup-py/_deduplicate_phases.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict with key 'modified_modules': an empty list if no source file path appeared more than once in the original phases.json, or a list of dicts each describing a module whose source_files list was altered. Each dict has keys 'phase' (int), 'module' (str), 'removed_files' (list of file paths removed from this module), and 'source_files' (this module's source_files after deduplication). After return, the phases.json file at phases_dir has been rewritten such that each source file path appears in at most one module's source_files list. When a path occurs in multiple locations, it is retained only in the occurrence with the smallest phase number  and earliest position within the modules list for that phase  and removed from all subsequent occurrences. Phases and modules whose source_files become empty are retained with their original position, numbering, and all non-source_files properties unchanged.

---

### Actual Behavior

Upon successful return (no exception raised), the file at `phases_dir/phases.json` has been overwritten with a JSON object that retains the original structure (phases array, phase numbers, module names, etc.) but each modules `source_files` list is filtered to contain only those file strings that had not appeared in any earlier module when traversing phases in ascending integer phase order and modules in their original array order. Thus, every distinct source file appears at most once globally, always in the earliest module that originally contained it. No phase or module is removed, even if a modules source_files becomes empty. The function returns a dictionary `{ 'modified_modules': [...] }` where the list contains, in traversal order, one entry per module whose source_files actually changed. Each entry is a dictionary with keys: `phase` (the integer phase number), `module` (modules name, defaulting to ''), `removed_files` (a list of the duplicate files removed, preserving their original relative order), and `source_files` (a copy of the modules final source_files list). If no duplicates existed, the list is empty. Formally: let `D0` be the original JSON from the file; let `order` be the total ordering of all file occurrences defined by (1) increasing `p['phase']`, (2) module index within `p['modules']`, (3) file index within `m['source_files']`. For each module `m` with original list `orig`, let `S` be the set of files from all earlier modules in `order`. Then the new list is `[f for f in orig if f  S]`. The modified `D0` is written back with `json.dump(..., indent=2)`. The returned `modified_modules` satisfies: for each module where `new != orig`, there is an entry in traversal order with `phase = containing_phase['phase']`, `module = m.get('name', '')`, `removed_files = [f for f in orig if f  new]`, and `source_files = list(new)`. All other fields of `D0` are unchanged. If an exception occurs, the file state and return are unspecified.

---

## Code Evidence

Line 18: for phase in sorted(data["phases"], key=lambda p: p["phase"]):
Line 44: "phase": phase["phase"],

---

## Trigger Condition

The code does not cast phase numbers to int before sorting, so string phases can produce an order that is not the numeric 'smallest phase number' required by the specification. Additionally, the returned 'phase' value preserves the original type, which may not be int.

---

## How to trigger the bug

When phase numbers are stored as strings in phases.json (e.g. from a JSON parser that preserves types, or from manual editing), `sorted(data["phases"], key=lambda p: p["phase"])` performs **lexicographic** sorting instead of numeric sorting. For example, phases `"10"` and `"2"` sort as `["10", "2"]` in lexicographic order instead of `[2, 10]` in numeric order. This causes phase 10 (larger numeric value) to be processed before phase 2 (smaller numeric value), violating the spec's requirement that duplicates are kept in the "smallest phase number" occurrence.

Additionally, the returned `"phase"` key preserves the original type from JSON (string), while the spec requires it to be `int`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_dir` | Temporary directory containing `phases.json` with phases `"10"` and `"2"`, both sharing file `"shared.py"` |

### Expected (spec-correct) Output

`modified_modules` should contain phase 10 (the larger phase) losing `shared.py`, because phase 2 (numeric 2) is the "smallest phase number" and should keep it. The returned `phase` values should be `int`s.

```json
{"modified_modules": [{"phase": 10, "module": "mod_a", "removed_files": ["shared.py"], "source_files": ["a.py"]}]}
```

### Actual (buggy) Output

`modified_modules` contains phase `"2"` (string) losing `shared.py`, because lexicographic sort processed phase `"10"` first and kept `shared.py` there. Phase `"2"` (numeric 2) should have kept it as the smallest phase, but lost it instead.

```json
{"modified_modules": [{"phase": "2", "module": "mod_b", "removed_files": ["shared.py"], "source_files": ["b.py"]}]}
```

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.pipeline_setup import _deduplicate_phases

with tempfile.TemporaryDirectory() as tmpdir:
    phases_data = {
        "phases": [
            {"phase": "10", "modules": [{"name": "mod_a", "source_files": ["shared.py", "a.py"]}]},
            {"phase": "2",  "modules": [{"name": "mod_b", "source_files": ["shared.py", "b.py"]}]},
        ]
    }
    with open(os.path.join(tmpdir, "phases.json"), "w") as f:
        json.dump(phases_data, f)
    result = _deduplicate_phases(tmpdir)
    # actual (buggy) output: phase "2" lost shared.py, phase "10" kept it
    # expected (correct) output: phase 10 lost shared.py, phase 2 kept it
    # Returned phase is str "2" instead of int 2
    print(result)
```

---

## Probe Script

```python
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from src.pipeline_setup import _deduplicate_phases

    with tempfile.TemporaryDirectory() as tmpdir:
        phases_path = os.path.join(tmpdir, "phases.json")

        # phases.json with string phase numbers: "10" and "2".
        # Numeric order: 2 < 10  → phase 2 should process first.
        # Lexicographic: "10" < "2" → phase "10" processes first (BUG).
        # Both phases share "shared.py" — the first-processed phase keeps it.
        phases_data = {
            "phases": [
                {
                    "phase": "10",
                    "modules": [
                        {"name": "mod_a", "source_files": ["shared.py", "a.py"]}
                    ],
                },
                {
                    "phase": "2",
                    "modules": [
                        {"name": "mod_b", "source_files": ["shared.py", "b.py"]}
                    ],
                },
            ]
        }
        with open(phases_path, "w") as f:
            json.dump(phases_data, f)

        result = _deduplicate_phases(tmpdir)
        modified = result.get("modified_modules", [])

        bug_confirmed = False
        issues = []

        # Check 1: If phase "2" (numeric 2) lost shared.py, that means phase "10"
        # was processed first (lexicographic sort of strings) — the BUG.
        for mod in modified:
            if str(mod["phase"]) == "2" and "shared.py" in mod.get(
                "removed_files", []
            ):
                bug_confirmed = True
                issues.append(
                    "Phase 2 (smaller numeric) lost shared.py to phase 10 (larger numeric) — "
                    "lexicographic sort of string phases produced wrong ordering"
                )
                break

        # Check 2: Returned phase values must be int per spec, but code preserves original type.
        for mod in modified:
            if not isinstance(mod["phase"], int):
                bug_confirmed = True
                issues.append(
                    f"Returned phase type is {type(mod['phase']).__name__} "
                    f"(value {mod['phase']!r}), spec requires int"
                )

        if bug_confirmed:
            print(f"CONFIRMED — {', '.join(issues)}")
        else:
            print(f"NOT CONFIRMED — phases sorted correctly despite string types")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — Phase 2 (smaller numeric) lost shared.py to phase 10 (larger numeric) — lexicographic sort of string phases produced wrong ordering, Returned phase type is str (value '2'), spec requires int
```
