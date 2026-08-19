# Bug Report: _trace_value

**Source file:** `fm_agent/extracted_functions/dashboard-py/_trace_value.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

For each field name in keys, in order, probes d for both the plain field name and its decorator-prefixed variants. Returns the value of the first field that has a truthy value in d. Returns None if no field named by keys has a truthy value under any recognized key form.

---

### Actual Behavior

After the function executes, the returned value ret satisfies: if d is not a dict, ret = None; if d is a dict, let C be the concatenated sequence of candidate strings obtained by iterating over the input keys in the given order and, for each key k, appending k, then '+' + k, then '*' + k. If no candidate in C is a key of d, ret = None; otherwise, let c be the first candidate in C that is a key of d, and ret = d[c].

---

## Code Evidence

Line 7: if candidate in d:
Line 8: return d[candidate]

---

## Trigger Condition

The code checks key existence in d, but the specification requires the field to have a truthy value. A falsy value for an existing key causes code to return that falsy value, while the specification expects it to be skipped.

---

## How to trigger the bug

The function uses `if candidate in d` to test key membership, but the spec requires testing whether the value is truthy. When a key exists in `d` but holds a falsy value (e.g., `0`, `""`, `None`, `False`, empty containers), the function returns that falsy value instead of skipping to the next candidate key or returning `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `d` | `{"status": 0}` |
| `keys` | `("status",)` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`0`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import _trace_value
print(_trace_value({"status": 0}, "status"))
# actual (buggy) output: 0
# expected (correct) output: None
```

---

## Probe Script

```python
import sys
import os

# Resolve the repo root from the probe's location
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, repo_root)

try:
    from dashboard import _trace_value
except Exception as e:
    print(f"ERROR: Failed to import dashboard._trace_value: {e}")
    sys.exit(1)

# Bug: code uses `if candidate in d` (key existence) but spec requires
# "first field that has a truthy value". A falsy value in an existing key
# causes code to return that falsy value instead of skipping it.
#
# Spec expects: skip falsy value 0 for key "status" → return None.
# Code does: key "status" exists in d → return d["status"] = 0.

try:
    actual = _trace_value({"status": 0}, "status")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if actual is not None:
    # Bug confirmed: returned falsy 0 instead of skipping to None
    print(f"CONFIRMED — actual: {actual!r} | expected (spec-correct): None")
else:
    print(f"NOT CONFIRMED — actual matched spec-expected: None")
```

### Probe Output

```
CONFIRMED — actual: 0 | expected (spec-correct): None
```
