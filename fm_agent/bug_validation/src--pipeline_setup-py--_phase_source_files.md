# Bug Report: _phase_source_files

**Source file:** `src/pipeline_setup-py/_phase_source_files.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When phases_json cannot be read (file missing, unreadable) or contains
    invalid JSON, returns an empty dict.
  - Otherwise returns a dict[int, list[str]] mapping each phase number
    present in the file to the concatenation of all source_files arrays
    from ALL modules within that phase. Phases whose "phase" key is
    absent or null are silently skipped.
  - The returned dict may contain entries whose value is an empty list
    if the corresponding phase has modules but no source files.
  - Each source file path in the returned lists is a string exactly as it
    appears in phases.json (no normalization, no resolution).

---

### Actual Behavior

The function returns a dictionary mapping each phase number (integer) to the combined list of source file paths (strings) from all modules of that phase, in the order they appear in the phases.json file. Formally, if the file is successfully opened and parsed as a valid JSON object with a 'phases' array conforming to the given schema, then result = {phase['phase']: [file for module in phase['modules'] for file in module['source_files']] for phase in D['phases']}. If the file cannot be opened or contains invalid JSON (contradicting the precondition), an empty dictionary is returned.

---

## Code Evidence

Line 13: for phase in data.get("phases", []):

---

## Trigger Condition

The specification states that if the JSON is valid and contains no phase numbers, the function should return an empty dict. The code does not verify that `data` is a dictionary before calling `.get()`, so a valid JSON array causes an unhandled `AttributeError` instead of returning `{}`.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phases_json` | Path to a file containing the valid JSON array `[]` |

### Expected (spec-correct) Output

`{}` (empty dict)

### Actual (buggy) Output

`AttributeError: 'list' object has no attribute 'get'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
import sys
repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, repo_root)
from src.pipeline_setup import _phase_source_files

with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
    f.write("[]")
    tmp = f.name

_phase_source_files(tmp)
# actual (buggy) output: AttributeError: 'list' object has no attribute 'get'
# expected (correct) output: {}
```

---

## Probe Script

```python
"""Probe for _phase_source_files: test that a valid JSON array (not object)
causes an AttributeError instead of returning {} per the specification."""
import sys
import os
import json
import tempfile

# Ensure repo root is on path so 'config' and 'src' resolve.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(repo_root)
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _phase_source_files
except Exception as e:
    print(f"ERROR: import {e}")
    sys.exit(1)

# ---- Test: valid JSON array instead of object -------------------------------
# The spec says: "When phases_json cannot be read (file missing, unreadable)
# or contains invalid JSON, returns an empty dict."
# However, a bare JSON array like '[]' is VALID JSON that json.load() will
# parse into a Python list, NOT a dict. The code then calls data.get("phases", [])
# which crashes with AttributeError because lists have no .get() method.

tmp_path = os.path.join(repo_root, "fm_agent", "bug_validation", "_tmp_probe_phases.json")

try:
    with open(tmp_path, "w") as f:
        f.write("[]")

    actual = _phase_source_files(tmp_path)

    # If we got here without an AttributeError, the function handled it.
    expected = {}  # spec says: invalid/unreadable → empty dict
    bug_present = not isinstance(actual, dict) or actual != expected

    if bug_present:
        print(f"CONFIRMED — valid JSON array returned non-empty: {actual!r} (expected: {{}})")
    else:
        print(f"NOT CONFIRMED — empty dict returned for JSON array as spec requires: {actual!r}")

except AttributeError as e:
    # The bug: data.get() failed because data is a list, not a dict.
    print(f"CONFIRMED — AttributeError on JSON array (expected empty dict per spec): {e}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
```

### Probe Output

```
CONFIRMED — AttributeError on JSON array (expected empty dict per spec): 'list' object has no attribute 'get'
```
