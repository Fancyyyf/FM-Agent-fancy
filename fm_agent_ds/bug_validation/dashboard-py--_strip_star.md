# Bug Report: _strip_star

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/dashboard-py/_strip_star.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict containing the same key-value pairs as d. For every string key: if the key in d starts with '*', the leading '*' is removed in the returned dict; otherwise the key is identical. Non-string keys are unchanged.

---

### Actual Behavior

If the input `d` is not a dictionary, the function returns `d` unchanged. If `d` is a dictionary, the function returns a new dictionary where for each key-value pair `k, v` in `d`, if `k` is a string starting with `'*'`, the key in the returned dictionary is `k[1:]` (the substring after the first character); otherwise the key remains `k`. The returned dictionary contains exactly the same set of values as the input dictionary, associated with the modified keys. The original input dictionary is not mutated. Formally: For any variable `d` satisfying the pre-condition, after `_strip_star(d)` executes, the result `r` satisfies: ( `not isinstance(d, dict)` implies `r is d` ) ∧ ( `isinstance(d, dict)` implies ( `r` is a new dictionary ∧ ∀ (k, v) ∈ d. ( (isinstance(k, str) ∧ k.startswith('*')) ⇒ (k[1:], v) ∈ r ) ∧ ( ¬(isinstance(k, str) ∧ k.startswith('*')) ⇒ (k, v) ∈ r ) ) ∧ `len(r)` = `len(d)` ) ).

---

## Code Evidence

```
Line 5: return {(k[1:] if k.startswith("*") else k): v for k, v in d.items()}
```

---

## Trigger Condition

The code unconditionally calls k.startswith("*") for every key k. When k is a non-string (e.g., the integer 1), it raises an AttributeError because integers do not have a startswith method. The specification requires that non-string keys be left unchanged, which would result in the dictionary {1: 'a'} being returned without an error. Thus the code's behavior (raising an exception) violates the specification for the valid input {1: 'a'}.

---

## How to trigger the bug

The function iterates over all dictionary keys and unconditionally calls `k.startswith("*")` on each key. When a key is not a string (e.g., an integer), the `startswith` call raises an `AttributeError` instead of leaving the non-string key unchanged as required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `d` | `{1: 'a'}` |

### Expected (spec-correct) Output

`{1: 'a'}`

### Actual (buggy) Output

`AttributeError: 'int' object has no attribute 'startswith'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard
dashboard._strip_star({1: "a"})
# actual (buggy) output: AttributeError: 'int' object has no attribute 'startswith'
# expected (correct) output: {1: 'a'}
```

---

## Probe Script

```python
import sys
import os
from pathlib import Path

# The probe runs from the repo root; ensure the repo root is on the path
# so that 'import dashboard' finds dashboard.py.
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent.parent
sys.path.insert(0, str(_repo_root))

try:
    import dashboard
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

actual = None
expected = {1: "a"}
passed = False
error_msg = None

try:
    actual = dashboard._strip_star({1: "a"})
    # If we get here without exception, the function returned successfully.
    # Check: did the non-string key survive unchanged as spec requires?
    passed = actual != expected
except AttributeError as e:
    # Bug confirmed: k.startswith("*") raised AttributeError on integer key
    error_msg = str(e)
    passed = True   # Bug reproduced: exception instead of returning unchanged
except Exception as e:
    error_msg = str(e)
    passed = False  # Unexpected error type

if passed:
    if error_msg:
        print(f"CONFIRMED — AttributeError raised on non-string key: {error_msg!r} | expected: {expected!r}")
    else:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — AttributeError raised on non-string key: "'int' object has no attribute 'startswith'" | expected: {1: 'a'}
```
