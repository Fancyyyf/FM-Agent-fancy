# Bug Report: _parse_spec_check_json

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/prompts-py/_parse_spec_check_json.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a 4-tuple (has_mismatch, offending_statements, reason, data). has_mismatch is True when the parsed JSON verdict is MISMATCH, False when MATCH. For MISMATCH: offending_statements and reason are non-empty strings. For MATCH: offending_statements is None and reason is None. data is a dict containing the full parsed and validated JSON object with verdict normalized to uppercase and keys: verdict, counterexample, offending_statements, reason. Raises ValueError when the response does not contain a valid spec-check JSON object: JSON is malformed, the parsed result is not a JSON object, any of the four required fields is missing, verdict is not 'MATCH' or 'MISMATCH' (case-insensitive), any field has an invalid type, or a MISMATCH verdict's counterexample, offending_statements, or reason is not a non-empty string.

---

### Actual Behavior

After the function executes, either a ValueError is raised or a 4-tuple is returned. The function first attempts to parse `response` into a dict using `_load_spec_check_json`. If `_load_spec_check_json` raises `json.JSONDecodeError`, a ValueError with message starting 'spec-check response is not valid JSON:' is raised. If the parsed result is not a dict, ValueError 'spec-check JSON must be an object' is raised. If the dict does not contain all required keys 'verdict', 'counterexample', 'offending_statements', 'reason', a ValueError listing missing fields is raised. The 'verdict' value is normalized: if it is a string it is uppercased; then if the result is not 'MATCH' or 'MISMATCH', a ValueError 'spec-check JSON verdict must be MATCH or MISMATCH' is raised. The fields 'counterexample' and 'offending_statements' must be either None or a string; otherwise a ValueError indicating the field must be string or null is raised. The 'reason' field must be a string; otherwise a ValueError 'spec-check JSON field reason must be a string' is raised. After these checks, the normalized verdict is stored back into the dict. 

If the verdict is 'MISMATCH', then 'counterexample', 'offending_statements', and 'reason' must all be non-empty strings after stripping whitespace; if any is empty or whitespace-only, a ValueError listing the offending fields is raised. Otherwise, these fields are stripped and stored, and the function returns (True, stripped_offending_statements, stripped_reason, modified_dict). 

If the verdict is 'MATCH', then neither 'counterexample' nor 'offending_statements' may be non-empty strings (i.e., they must be either None or whitespace-only/empty strings). If either contains non-whitespace text, a ValueError 'spec-check MATCH JSON must not include counterexample or offending_statements' is raised. Otherwise, 'counterexample' and 'offending_statements' are set to None in the dict, 'reason' is stripped and stored, and the function returns (False, None, None, modified_dict).

---

## Code Evidence

Line 47: if \_nonempty_string(counterexample) or \_nonempty_string(offending\_statements):
Line 48:         raise ValueError(
Line 49:             "spec-check MATCH JSON must not include counterexample or offending\_statements"
Line 50:         )

---

## Trigger Condition

The code raises a ValueError for a valid MATCH verdict with non-empty counterexample, but the specification does not require MATCH verdicts to have empty counterexample/offending\_statements. This rejects a valid input.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| response | `{"verdict": "MATCH", "counterexample": "a concrete counterexample", "offending_statements": null, "reason": "all good"}` |

### Expected (spec-correct) Output

`(False, None, None, {"verdict": "MATCH", "counterexample": None, "offending_statements": None, "reason": "all good"})`

### Actual (buggy) Output

`ValueError("spec-check MATCH JSON must not include counterexample or offending_statements")`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.prompts import _parse_spec_check_json

response = '{"verdict": "MATCH", "counterexample": "a concrete counterexample", "offending_statements": null, "reason": "all good"}'

try:
    result = _parse_spec_check_json(response)
    print("No error (spec-correct):", result)
except ValueError as e:
    # actual (buggy) output: ValueError("spec-check MATCH JSON must not include counterexample or offending_statements")
    print("ValueError raised (buggy):", e)
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script for bug: _parse_spec_check_json rejects MATCH verdict with non-empty counterexample."""

import sys
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _REPO_ROOT)

try:
    from src.prompts import _parse_spec_check_json

    # -----------------------------------------------------------------------
    # Test 1: MATCH verdict with non-empty counterexample (offending_statements is null)
    # Spec: does NOT list this as a ValueError case → should be accepted
    # Code: line 87-90 raises ValueError
    # -----------------------------------------------------------------------
    response1 = (
        '{"verdict": "MATCH",'
        ' "counterexample": "a concrete counterexample",'
        ' "offending_statements": null,'
        ' "reason": "all good"}'
    )

    actual1 = None
    error1 = None
    try:
        actual1 = _parse_spec_check_json(response1)
    except ValueError as e:
        error1 = str(e)

    if error1 is not None:
        print(f"CONFIRMED — bug reproduced: ValueError raised for valid MATCH verdict with non-empty counterexample")
        print(f"  Expected: should return (False, None, None, data)")
        print(f"  Actual error: {error1}")
    else:
        print(f"NOT CONFIRMED — function accepted MATCH with non-empty counterexample (spec-correct)")
        print(f"  Returned: {actual1!r}")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — bug reproduced: ValueError raised for valid MATCH verdict with non-empty counterexample
  Expected: should return (False, None, None, data)
  Actual error: spec-check MATCH JSON must not include counterexample or offending_statements
```
