# Bug Report: phase_callee_info_names_key

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_batch_prompts-py/phase_callee_info_names_key.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the string key in func whose name is the concatenation of "phase", the decimal string representation of phase, and "_callee_info_names_by_caller" when such a key exists. Returns None when func does not contain a key formed by this concatenation.

---

### Actual Behavior

func is unchanged from its pre-state (the dictionary is not modified). The return value r is of type None or str, and it satisfies: (r is None) if and only if for every key k in func, either not k.startswith("phase") or not k.endswith("_callee_info_names_by_caller"). If there exists at least one key k in func with k.startswith("phase") and k.endswith("_callee_info_names_by_caller"), then r is such a key; moreover, if the specific key "phase{phase}_callee_info_names_by_caller" (where {phase} is the given positive integer) is present in func, then r equals that key. No exceptions are raised; the function terminates normally.

---

## Code Evidence

Line 5: for key in func.keys():
Line 6: if key.endswith("_callee_info_names_by_caller") and key.startswith("phase"):
Line 7: return key

---

## Trigger Condition

The code returns any key matching the pattern when the exact target is missing, but the specification requires returning None if the exact key is absent.

---

## How to trigger the bug

When `func` contains `"phase2_callee_info_names_by_caller"` but NOT `"phase1_callee_info_names_by_caller"`, calling `phase_callee_info_names_key(func, 1)` should return `None` (per the spec, since the exact key for phase 1 is absent). Instead, the buggy fallback loop on lines 5-7 matches `"phase2_callee_info_names_by_caller"` and returns it — leaking a key belonging to a different phase.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func` | `{"phase2_callee_info_names_by_caller": {"callerA": ["info1"]}, "phase2_callers": ["callerA"]}` |
| `phase` | `1` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`'phase2_callee_info_names_by_caller'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_batch_prompts import phase_callee_info_names_key

func = {
    "phase2_callee_info_names_by_caller": {"callerA": ["info1"]},
    "phase2_callers": ["callerA"],
}

result = phase_callee_info_names_key(func, 1)
# actual (buggy) output: 'phase2_callee_info_names_by_caller'
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe for phase_callee_info_names_key bug: when exact target key is absent,
the buggy code returns any key matching the pattern instead of None."""

import sys
import os

# Work from a temp directory per the self-validation guard, but we can
# still import from the project root. Add the (absolute) project root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

try:
    from src.generate_batch_prompts import phase_callee_info_names_key

    # Construct a dict that has a phase-2 key but no phase-1 key.
    func = {
        "phase2_callee_info_names_by_caller": {"callerA": ["info1"]},
        "phase2_callers": ["callerA"],
    }

    # Looking for phase 1 - the exact key "phase1_callee_info_names_by_caller"
    # does NOT exist in func, so the spec requires None.
    actual = phase_callee_info_names_key(func, 1)
    expected = None  # per specification: return None when exact key is absent

    passed = actual != expected  # True means bug reproduced

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: 'phase2_callee_info_names_by_caller' | expected: None
```
