# Bug Report: _collect_changed_phases

**Source file:** `src/pipeline_setup-py/_collect_changed_phases.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a set containing every non-None integer that is either:
    a) a key of ensure_changes["augmented"], or
    b) the value of the "phase" key from any entry in "modified_modules" across all change_sets.
  - Each phase number appears at most once in the result (duplicates are collapsed).
  - Returns an empty set if no non-None phase numbers are found across all sources.

---

### Actual Behavior

The function returns a set of distinct non-None phase numbers (integers, as per the precondition) collected from two sources. 1) Every key k in ensure_changes["augmented"] (if the key exists and the value is a mapping) for which k is not None is included. 2) For every change set c in *change_sets, and for every module m in c.get("modified_modules", []), the value m.get("phase") is included if it is not None. Formally, if we denote A = ensure_changes.get("augmented", {}) and for each c  change_sets, M(c) = c.get("modified_modules", []), then the returned set is: {k | k  A.keys()  k  None}  {m.get("phase") | c  change_sets, m  M(c)  m.get("phase")  None}.

---

## Code Evidence

Line 16:         if phase_num is not None:
Line 17:             phases.add(phase_num)
Line 21:         if phase_num is not None:
Line 22:             phases.add(phase_num)

---

## Trigger Condition

The code only checks for None but does not verify that the phase numbers are integers. The specification requires the returned set to contain only non-None integers, so non-integers like strings or floats should be excluded.

---

## How to trigger the bug

The function has two code paths that collect phase numbers: (1) keys from `ensure_changes["augmented"]` and (2) `"phase"` values from `modified_modules` entries. Both paths only guard against `None` but do not check `isinstance(phase_num, int)`. Passing a non-integer value (string or float) in either path causes it to appear in the result set, violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `ensure_changes` (test 1) | `{"augmented": {5: True, "abc": True, None: True}}` |
| `ensure_changes` (test 2) | `{}` |
| `*change_sets` (test 2) | `({"modified_modules": [{"phase": 10}, {"phase": 3.14}, {"phase": None}]},)` |

### Expected (spec-correct) Output

Test 1: `{5}` — only the integer key, since `"abc"` is not a non-None integer and `None` is excluded.
Test 2: `{10}` — only the integer phase value, since `3.14` is a float (not an integer) and `None` is excluded.

### Actual (buggy) Output

Test 1: `{5, "abc"}` — the string `"abc"` was included.
Test 2: `{10, 3.14}` — the float `3.14` was included.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.pipeline_setup import _collect_changed_phases

# Test 1: string key in augmented
result = _collect_changed_phases({"augmented": {5: True, "abc": True, None: True}})
# actual (buggy) output: {5, 'abc'}
# expected (correct) output: {5}

# Test 2: float phase in modified_modules
result = _collect_changed_phases({},
    {"modified_modules": [{"phase": 10}, {"phase": 3.14}, {"phase": None}]})
# actual (buggy) output: {10, 3.14}
# expected (correct) output: {10}
```

---

## Probe Script

```python
"""Probe for _collect_changed_phases: test that non-integer phase numbers are
erroneously included when only None is checked."""
import sys
import os

# Ensure repo root is on path so 'config' and 'src' resolve.
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(repo_root)
sys.path.insert(0, repo_root)

try:
    from src.pipeline_setup import _collect_changed_phases
except Exception as e:
    print(f"ERROR: import {e}")
    sys.exit(1)

# ---- Test 1: non-integer string as augmented key --------------------------
# The spec says only non-None integers should appear.  A string should be
# excluded, but the code only guards against None.
try:
    ensure_changes = {"augmented": {5: True, "abc": True, None: True}}
    result = _collect_changed_phases(ensure_changes)

    # Spec requires result to contain only non-None integers.
    non_ints_in_result = [v for v in result if not isinstance(v, int)]
    bug_present = len(non_ints_in_result) > 0

    display_actual = sorted(result, key=str)

    if bug_present:
        print(f"CONFIRMED — augmented-keys: included non-integers {non_ints_in_result!r} "
              f"| full result={display_actual!r}")
    else:
        print(f"NOT CONFIRMED — augmented-keys: result contains only integers: {display_actual!r}")
except Exception as e:
    print(f"ERROR: test1 {e}")
    sys.exit(1)

# ---- Test 2: non-integer float as modified_modules phase ------------------
try:
    change_sets = ({"modified_modules": [
        {"phase": 10},
        {"phase": 3.14},   # float — not an integer, should be excluded per spec
        {"phase": None},
    ]},)
    result2 = _collect_changed_phases({}, *change_sets)

    non_ints2 = [v for v in result2 if not isinstance(v, int)]
    bug_present2 = len(non_ints2) > 0

    display_actual2 = sorted(result2, key=str)

    if bug_present2:
        print(f"CONFIRMED — modified_modules: included non-integers {non_ints2!r} "
              f"| full result={display_actual2!r}")
    else:
        print(f"NOT CONFIRMED — modified_modules: result contains only integers: {display_actual2!r}")
except Exception as e:
    print(f"ERROR: test2 {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — augmented-keys: included non-integers ['abc'] | full result=[5, 'abc']
CONFIRMED — modified_modules: included non-integers [3.14] | full result=[10, 3.14]
```
