# Bug Report: _domain_context_complete

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True if and only if all of the following hold simultaneously:
    (a) phases.json exists under work_dir and is a well-formed JSON file
        containing a "phases" array
    (b) spec_prompts/domain_context/engine_overview.txt exists as a regular
        file under work_dir
    (c) For every phase object in phases.json whose "phase" key is a numeric
        value, the file spec_prompts/domain_context/phase_NN_types.txt
        (where NN is the phase number zero-padded to 2 digits) exists as a
        regular file under work_dir
    (d) No phase object in phases.json has a missing or non-numeric "phase"
        key
  - Returns False when any of conditions (a)-(d) is not satisfied
  - Does not modify any filesystem state: the function performs only
    existence checks and reads, never creates, updates, or deletes files

---

### Actual Behavior

After execution, the function returns a boolean value. 

Natural language: 
The function returns True if and only if: 
1. The file `phases.json` inside `work_dir` is a valid JSON file (i.e., it exists as a regular file and its content is successfully parseable as JSON). 
2. The file `spec_prompts/domain_context/engine_overview.txt` relative to `work_dir` exists as a regular file. 
3. The parsed JSON object from `phases.json` contains a key `'phases'` whose value is a list. For every element `phase_entry` in that list, `phase_entry` contains a key `'phase'` with a nonnull numeric value, and the file `spec_prompts/domain_context/phase_{phase_num:02d}_types.txt` (where `phase_num` is that numeric value formatted to two digits) exists as a regular file. 
If any of these conditions fails, the function returns False. All file handles are properly closed by the context manager. No exception is raised to the caller; any `OSError` or `json.JSONDecodeError` is caught and results in a `False` return. 

Formal logic (using higherorder predicates): 
Let 
  `PhasesPath = Join(work_dir, "phases.json")` 
  `DomainDir = Join(work_dir, "spec_prompts", "domain_context")` 
  `EngOverviewPath = Join(DomainDir, "engine_overview.txt")` 
Define 
  `IsValidJSONFile(p) ::= p refers to an existing regular file whose contents are valid JSON` 
  `ExistsRegFile(p) ::= p refers to an existing regular file` 
Then, the return value `R` satisfies: 
  `R = True    IsValidJSONFile(PhasesPath) 
                 ExistsRegFile(EngOverviewPath) 
                 ( D such that D = parse_json(PhasesPath)  
                   (D["phases"] is a list  
                     i  [0 .. |D["phases"]|-1] : 
                      D["phases"][i] has key "phase"  
                      D["phases"][i]["phase"]  None  
                      ExistsRegFile(Join(DomainDir, 
                        "phase_" + format(int(D["phases"][i]["phase"]), '02d... 

---

## Code Evidence

Line 649: `types_path = os.path.join(domain_dir, f"phase_{phase_num:02d}_types.txt")`

---

## Trigger Condition

The code assumes phase_num is numeric, but phase_num may be a non-numeric string that is not None. The specification requires returning False when a phase key is non-numeric, not raising an exception.

---

## How to trigger the bug

The function `_domain_context_complete` iterates over phases in `phases.json` and builds a filename using `f"phase_{phase_num:02d}_types.txt"`. The `:02d` format specifier requires `phase_num` to be an integer. When a phase object has a non-numeric string value for its `"phase"` key, the format string raises a `ValueError` which propagates out of the function. The specification requires the function to return `False` in this case, never to raise an exception.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | A temporary directory containing a valid `phases.json` with `{"phases": [{"phase": 1}, {"phase": "not_a_number"}]}`, plus `spec_prompts/domain_context/engine_overview.txt` and `spec_prompts/domain_context/phase_01_types.txt` |

### Expected (spec-correct) Output

`False` (the function should return False when a phase key is non-numeric)

### Actual (buggy) Output

`ValueError: Unknown format code 'd' for object of type 'str'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import tempfile, os, json, shutil
from src.pipeline_setup import _domain_context_complete

work_dir = tempfile.mkdtemp()
try:
    phases = {"phases": [{"phase": 1}, {"phase": "not_a_number"}]}
    with open(os.path.join(work_dir, "phases.json"), "w") as f:
        json.dump(phases, f)
    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)
    with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
        f.write("overview")
    with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
        f.write("types")
    result = _domain_context_complete(work_dir)
    print(result)  # unreachable — ValueError raised first
finally:
    shutil.rmtree(work_dir, ignore_errors=True)

# actual (buggy) output: ValueError: Unknown format code 'd' for object of type 'str'
# expected (correct) output: False
```

---

## Probe Script

```python
import sys
import os
import json
import tempfile
import shutil

# Add repo root to path so `src` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.pipeline_setup import _domain_context_complete
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

work_dir = tempfile.mkdtemp()
try:
    # phases.json: first phase is numeric (valid), second phase has non-numeric key
    phases = {
        "phases": [
            {"phase": 1},
            {"phase": "not_a_number"}
        ]
    }
    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path, "w") as f:
        json.dump(phases, f)

    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    os.makedirs(domain_dir, exist_ok=True)

    with open(os.path.join(domain_dir, "engine_overview.txt"), "w") as f:
        f.write("overview")

    with open(os.path.join(domain_dir, "phase_01_types.txt"), "w") as f:
        f.write("types")

    expected = False  # spec: return False when phase key is non-numeric

    try:
        actual = _domain_context_complete(work_dir)
        # No exception: value was returned
        if actual != expected:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r} (spec says return False for non-numeric phase key)")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    except ValueError as e:
        # ValueError from f"{phase_num:02d}" when phase_num is non-numeric
        print(f"CONFIRMED — ValueError: {e} | spec says return False (no exception)")
    except Exception as e:
        print(f"ERROR: Unexpected {type(e).__name__}: {e}")
        sys.exit(1)
finally:
    shutil.rmtree(work_dir, ignore_errors=True)
```

### Probe Output

```
CONFIRMED — ValueError: Unknown format code 'd' for object of type 'str' | spec says return False (no exception)
```
