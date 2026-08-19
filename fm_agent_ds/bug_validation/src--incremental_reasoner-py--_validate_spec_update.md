# Bug Report: _validate_spec_update

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When data is not a dict, returns None. When data is a dict but is missing any of the required keys (spec_updated, new_spec, info_updated, new_info, updated_callees), or spec_updated is not a boolean, or info_updated is not a boolean, or updated_callees is not a list of non-empty strings, returns None. When spec_updated is true and new_spec is not a dict with 'signature', 'pre_condition', 'post_condition' keys whose values are all strings, returns None. When info_updated is true and new_info is not a dict containing a 'callees' key whose value is a list, returns None. Otherwise, returns a dict with exactly five keys: spec_updated (bool), new_spec (dict with 'signature', 'pre_condition', 'post_condition' string values, or null when spec_updated is false), info_updated (bool), new_info (dict with a 'callees' key, or null when info_updated is false), updated_callees (list of non-empty strings, each stripped of leading and trailing whitespace).

---

### Actual Behavior

After executing _validate_spec_update(data), one of the following holds: (1) ValueError('spec-update JSON must be an object') is raised if data is not a dict. (2) ValueError('spec-update JSON missing required field(s): ...') is raised if data is a dict but lacks any of 'spec_updated','new_spec','info_updated','new_info','updated_callees'. (3) ValueError('spec-update JSON fields spec_updated and info_updated must be booleans') is raised if data['spec_updated'] or data['info_updated'] is not a bool. (4) ValueError('spec-update JSON field updated_callees must be an array of non-empty strings') is raised if data['updated_callees'] is not a list or any element is not a non-empty string. (5) If data['spec_updated'] is True and data['new_spec'] is not a dict, ValueError('spec-update JSON requires object new_spec when spec_updated is true') is raised; if it is a dict but _is_valid_spec_json returns False, ValueError('spec-update JSON new_spec must match the .spec.json schema') is raised. (6) If data['info_updated'] is True and data['new_info'] is not a dict, ValueError('spec-update JSON requires object new_info when info_updated is true') is raised; if it is a dict but _is_valid_info_json returns False, ValueError('spec-update JSON new_info must match the .info.json schema') is raised. (7) Otherwise the function returns a dict r with keys: 'spec_updated' = data['spec_updated']; 'new_spec' = _normalize_spec_dict(data['new_spec']) if data['spec_updated'] else None; 'info_updated' = data['info_updated']; 'new_info' = _normalize_info_dict(data['new_info']) if data['info_updated'] else None; 'updated_callees' = [name.strip() for name in data['updated_callees']].

---

## Code Evidence

Line 4: raise ValueError("spec-update JSON must be an object")

---

## Trigger Condition

The specification requires returning None when data is not a dict, but the code raises a ValueError. This is a concrete violation for all non-dict inputs.

---

## How to trigger the bug

The function `_validate_spec_update` raises `ValueError('spec-update JSON must be an object')` when called with any non-dict argument (e.g., a string), whereas the specification states it should return `None` for such inputs.

### Inputs

| Parameter | Value |
|-----------|-------|
| data | `"not a dict"` (a string, or any non-dict value) |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`ValueError('spec-update JSON must be an object')` is raised.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.incremental_reasoner import _validate_spec_update
_validate_spec_update("not a dict")
# actual (buggy) output: ValueError: spec-update JSON must be an object
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe script for bug src--incremental_reasoner-py--_validate_spec_update.

Spec claim: _validate_spec_update(data) returns None when data is not a dict.
Actual behavior: _validate_spec_update(data) raises ValueError('spec-update JSON must be an object').
"""

import sys
import os

# Add the repo root to the path so we can import src.incremental_reasoner
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from src.incremental_reasoner import _validate_spec_update

    passed = False
    try:
        result = _validate_spec_update("not a dict")
        print(f"NOT CONFIRMED — no ValueError raised, returned: {result!r}")
        sys.exit(0)
    except ValueError as e:
        expected_return = None
        actual_behavior = f"ValueError: {e}"
        print(f"CONFIRMED — actual: {actual_behavior!r} | expected: {expected_return!r}")
        sys.exit(0)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'ValueError: spec-update JSON must be an object' | expected: None
```
