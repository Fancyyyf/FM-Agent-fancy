# Bug Report: _collect_changed_phases

**Source file:** `src/pipeline_setup.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a set of unique integer phase numbers aggregated from the provided change-tracking data structures. The returned set contains: (1) every non-None key from ensure_changes["augmented"] (when that key exists), representing phase numbers whose source-file composition was force-augmented; and (2) every non-None value associated with the key "phase" in every entry of each change_set["modified_modules"] list (when those keys exist), representing phase numbers whose module composition was modified. The returned set may be empty if no phase numbers are present in the input data structures. No element in the returned set equals None.

---

### Actual Behavior

If the function terminates normally (no exception propagated), the return value is a set containing every non-None key from `ensure_changes.get('augmented', {})` and every non-None value obtained by calling `get('phase')` on each element of each `changes.get('modified_modules', [])` for all `changes` in `change_sets`. In formal terms: let A = ensure_changes.get('augmented', {}) and B = {m for changes in change_sets for m in changes.get('modified_modules', [])}. Then result = {k | k  A  k  None}  {m.get('phase') | m  B  m.get('phase')  None}. If any of the iterations over A or B fails because the object is not iterable, a TypeError is raised; if any element m of B does not have a `get` method, an AttributeError is raised. In such exceptional cases the function does not return.

---

## Code Evidence

Line 15-17: for phase_num in ensure_changes.get("augmented", {}): if phase_num is not None: phases.add(phase_num)

---

## Trigger Condition

The code adds any non-None key from the 'augmented' mapping into the result set without verifying that the key is an integer. The specification mandates that the returned set consist exclusively of integer phase numbers. Input {"augmented": {"invalid": "value"}} causes the code to include the non-integer key "invalid", resulting in a set that contains a string, which violates the specification.

---

## How to trigger the bug

The function iterates over keys of `ensure_changes.get("augmented", {})` and adds them to the result set without checking that each key is an integer. When a non-integer key such as a string is present, it is included in the returned set, violating the specification that the set must contain only unique integer phase numbers.

### Inputs

| Parameter | Value |
|-----------|-------|
| `ensure_changes` | `{"augmented": {"invalid": "value", 1: "valid"}}` |
| `*change_sets` | *(none)* |

### Expected (spec-correct) Output

`{1}` — only the integer key `1` should be included.

### Actual (buggy) Output

`{1, "invalid"}` — the string key `"invalid"` is included because there is no type guard.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
from src.pipeline_setup import _collect_changed_phases

ensure_changes = {"augmented": {"invalid": "value", 1: "valid"}}
result = _collect_changed_phases(ensure_changes)
# actual (buggy) output: {1, "invalid"}
# expected (correct) output: {1}
```

---

## Probe Script

```python
import sys
import os

# When run from repo root via `python3 fm_agent/bug_validation/probe_<id>.py`,
# os.getcwd() is the repo root. Add it to sys.path.
_repo_root = os.getcwd()
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.pipeline_setup import _collect_changed_phases

    # The spec_claim: returned set contains "unique integer phase numbers"
    # The actual code: adds non-None keys from 'augmented' dict without type check
    # Trigger: {"augmented": {"invalid": "value"}} includes the string key "invalid"
    ensure_changes = {"augmented": {"invalid": "value", 1: "valid"}}

    actual = _collect_changed_phases(ensure_changes)

    # Spec-expected: only integer keys → {1}
    # Buggy actual:   includes the string key "invalid" → {"invalid", 1}
    expected = {1}

    if actual != expected:
        print(
            f"CONFIRMED — actual: {sorted(actual, key=str)!r} "
            f"| expected: {sorted(expected)!r}"
        )
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    import traceback

    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: [1, 'invalid'] | expected: [1]
```
