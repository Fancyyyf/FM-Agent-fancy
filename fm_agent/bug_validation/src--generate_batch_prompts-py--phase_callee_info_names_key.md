# Bug Report: phase_callee_info_names_key

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/generate_batch_prompts-py/phase_callee_info_names_key.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If func contains a key exactly equal to the string
    "phase<phase>_callee_info_names_by_caller" (where <phase> is the decimal
    representation of the phase argument), returns that exact key string
  - Otherwise, if func contains any key that starts with "phase" and ends with
    "_callee_info_names_by_caller", returns that key string
  - Otherwise, returns None
  - The return value is either a string that is an actual key present in func,
    or None

---

### Actual Behavior

The function returns either a string or None. Let target = f"phase{phase}_callee_info_names_by_caller". If target is a key in the dictionary func, the function returns target. Otherwise, it iterates over the keys of func in insertion order and returns the first key that starts with "phase" and ends with "_callee_info_names_by_caller". If no such key exists, it returns None. The dictionary func and integer phase are unchanged. Formally, define P(k)  str(k).startswith("phase")  str(k).endswith("_callee_info_names_by_caller"), T = "phase" + str(phase) + "_callee_info_names_by_caller". Then the return value r satisfies: (if T  func.keys() then r = T) else (if  k  func.keys() such that P(k) then let K = [k for k in func.keys() if P(k)] in insertion order; r = K[0]) else (r = None).

---

## Code Evidence

Line 5: for key in func.keys():
Line 6: if key.endswith("_callee_info_names_by_caller") and key.startswith("phase"):
Line 7: return key

---

## Trigger Condition

When the exact target key is absent and a non-string key like the integer 1 appears before the matching string key, the code calls .startswith('phase') on the integer, raising AttributeError. The specification requires returning the matching string key or None, not crashing.

---

## How to trigger the bug

When `phase_callee_info_names_key` is called with a dict containing a non-string key (e.g., `int`) that appears before any matching string key, and the exact target key is absent from the dict, the iteration loop attempts to call `.endswith()` on the non-string key, causing an `AttributeError`. The specification requires the function to return a matching string key or `None` — it should never crash on unexpected key types.

### Inputs

| Parameter | Value |
|-----------|-------|
| func | `{1: "value", "phase0_callee_info_names_by_caller": "matching"}` |
| phase | `1` |

### Expected (spec-correct) Output

`"phase0_callee_info_names_by_caller"` — the key starts with `"phase"` and ends with `"_callee_info_names_by_caller"`.

### Actual (buggy) Output

`AttributeError: 'int' object has no attribute 'endswith'` — the iteration hits the integer key `1` first and crashes when trying to call string methods on it.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_batch_prompts import phase_callee_info_names_key

func = {1: "value", "phase0_callee_info_names_by_caller": "matching"}
phase = 1
result = phase_callee_info_names_key(func, phase)
# actual (buggy) output: AttributeError: 'int' object has no attribute 'endswith'
# expected (correct) output: "phase0_callee_info_names_by_caller"
```

---

## Probe Script

```python
import sys

try:
    from src.generate_batch_prompts import phase_callee_info_names_key

    # The exact target key for phase=1 ("phase1_callee_info_names_by_caller")
    # is NOT in the dict, so the code enters the iteration loop.
    # The int key 1 appears BEFORE the matching string key.
    # Per spec: should find "phase0_callee_info_names_by_caller" (starts with
    # "phase", ends with "_callee_info_names_by_caller") and return it.
    # Per buggy code: crashes with AttributeError on int key 1.
    func = {1: "value", "phase0_callee_info_names_by_caller": "matching"}
    phase = 1

    expected = "phase0_callee_info_names_by_caller"
    actual = phase_callee_info_names_key(func, phase)

    # If we reach here, the code didn't crash. Bug is reproduced if
    # the returned value doesn't match the expected spec-correct output.
    passed = actual != expected

except AttributeError as e:
    # Bug CONFIRMED: crashed on non-string key when it should return a value
    print(f"CONFIRMED — AttributeError on non-string key: {e}")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — AttributeError on non-string key: 'int' object has no attribute 'endswith'
```
