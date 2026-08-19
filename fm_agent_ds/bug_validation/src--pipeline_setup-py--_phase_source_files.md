# Bug Report: _phase_source_files

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/pipeline_setup-py/_phase_source_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the file at phases_json is readable and contains a valid JSON object with a 'phases' array, returns a dict mapping each integer 'phase' value found in that array to the list of source file paths (strings) accumulated from the 'source_files' arrays of all modules belonging to that phase. Phase entries whose 'phase' key is missing or non-integer are excluded from the result. If the file cannot be read or its content is not a valid JSON object with a 'phases' array, returns an empty dict {}.

---

### Actual Behavior

After the function call, one of the following holds:

1. An OSError or ValueError was raised during the attempt to open or parse the file at `phases_json`. The function catches these exceptions and returns an empty dictionary `{}`.
2. No such exception occurred, but an unhandled exception (e.g., TypeError due to unexpected JSON structure) is raised during processing of the parsed data. In this case, the function does not return normally; the exception propagates to the caller.
3. No exception occurs (or only the caught exceptions). The function returns a dictionary `result` constructed as follows:
   - Let `data` be the result of `json.load(f)`.
   - `result` has a key for every phase number `n` that appears as the value of `phase["phase"]` for some `phase` in `data.get("phases", [])`, provided that value is not `None`.
   - For each such phase number `n`, the value `result[n]` is a list of strings, equal to the concatenation (in order of appearance) of the lists `module.get("source_files", [])` for all modules in `phase.get("modules", [])`. If a phase has no modules or no source files, the value is an empty list `[]`.

Formally:
Let `D = json.load(open(phases_json))` if that operation succeeds without raising `OSError` or `ValueError`.
If `open` or `json.load` raises `OSError` or `ValueError`, then the return value is exactly `{}`.
Otherwise, if during the iteration over `D["phases"]`, `p["phase"]` is accessed where `p` is a phase object, or during `module["source_files"]` an uncaught exception occurs, the function raises that exception and does not return.
Assuming no uncaught exception, the return value `result` satisfies:
```
result = { p["phase"] : 
           [ f for m in p.get("modules", []) for f in m.get("source_files", []) ]
           for p in D.get("phases", [])
           if "phase" in p and p["phase"] is not None
         }
```

---

## Code Evidence

Line 14: phase_num = phase.get("phase")
Line 15: if phase_num is None:
Line 16:     continue
Line 17: files = result.setdefault(phase_num, [])

---

## Trigger Condition

The specification requires that non-integer phase values be excluded from the result. The code only checks for missing phase key (None), so a phase entry with a string phase like 'abc' is included in the returned dictionary, violating the spec.

---

## How to trigger the bug

The bug is triggered when `phases.json` contains a phase entry whose `"phase"` value is a non-integer (e.g., a string like `"abc"`). The code only checks `if phase_num is None: continue` at line 15-16, so a string value passes the guard and gets used as a dictionary key. The specification requires that non-integer phase values be excluded.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | Path to a JSON file containing `{"phases": [{"phase": 1, ...}, {"phase": "abc", ...}]}` |

### Expected (spec-correct) Output

`{1: ['src/a.py']}`

### Actual (buggy) Output

`{1: ['src/a.py'], 'abc': ['src/b.py']}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
from src.pipeline_setup import _phase_source_files

with tempfile.TemporaryDirectory() as tmpdir:
    path = os.path.join(tmpdir, "phases.json")
    with open(path, "w") as f:
        json.dump({"phases": [
            {"phase": 1, "modules": [{"name": "mod_a", "source_files": ["src/a.py"]}]},
            {"phase": "abc", "modules": [{"name": "mod_b", "source_files": ["src/b.py"]}]}
        ]}, f)
    result = _phase_source_files(path)
    print(result)
# actual (buggy) output: {1: ['src/a.py'], 'abc': ['src/b.py']}
# expected (correct) output: {1: ['src/a.py']}
```

---

## Probe Script

```python
"""Probe: _phase_source_files should exclude non-integer phase values.

Bug: The function only checks for None, so a string phase like 'abc' is included
in the returned dictionary, violating the spec that says non-integer values
must be excluded.
"""

import sys
import json
import os
import tempfile

# Ensure the repo root is on the Python path so 'src' can be found.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_script_dir))  # up two levels
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def run_probe():
    # Create a temporary phases.json with a non-integer phase value.
    with tempfile.TemporaryDirectory() as tmpdir:
        phases_json_path = os.path.join(tmpdir, "phases.json")
        phases_data = {
            "phases": [
                {
                    "phase": 1,
                    "name": "Valid Phase",
                    "modules": [
                        {
                            "name": "mod_a",
                            "source_files": ["src/a.py"]
                        }
                    ]
                },
                {
                    "phase": "abc",  # Non-integer phase — spec says exclude
                    "name": "String Phase",
                    "modules": [
                        {
                            "name": "mod_b",
                            "source_files": ["src/b.py"]
                        }
                    ]
                }
            ]
        }
        with open(phases_json_path, "w") as f:
            json.dump(phases_data, f)

        # Import the function from the package module.
        from src.pipeline_setup import _phase_source_files

        result = _phase_source_files(phases_json_path)

        # Check results
        actual_keys = list(result.keys())
        has_string_key = any(isinstance(k, str) for k in actual_keys)

        if has_string_key and "abc" in result:
            actual = dict(result)  # for display
            expected = {1: ["src/a.py"]}  # spec: only integer phases
            print(
                f"CONFIRMED — Non-integer phase key 'abc' present in result. "
                f"actual: {actual!r} | expected: {expected!r}"
            )
        elif not has_string_key:
            print(
                f"NOT CONFIRMED — Non-integer phase was correctly excluded. "
                f"actual keys: {actual_keys!r}"
            )
        else:
            print(
                f"NOT CONFIRMED — Unexpected result: {result!r}"
            )


if __name__ == "__main__":
    try:
        run_probe()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

### Probe Output

```
CONFIRMED — Non-integer phase key 'abc' present in result. actual: {1: ['src/a.py'], 'abc': ['src/b.py']} | expected: {1: ['src/a.py']}
```
