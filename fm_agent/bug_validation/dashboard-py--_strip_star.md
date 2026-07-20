# Bug Report: _strip_star

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/dashboard-py/_strip_star.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If d is a dict, returns a new dict with the same key-value pairs
    as d, except that every key whose string representation starts with
    "*" has that leading "*" character stripped from the key.
    Keys that do not start with "*" are unchanged.
  - Every value in the returned dict is the identical object reference
    as the corresponding value in d (values are not copied or
    transformed).
  - The input dict d is not mutated.
  - If d is not a dict, returns d unchanged.

---

### Actual Behavior

If the input d is not a dictionary, the function returns d unchanged. If d is a dictionary, the function returns a new dictionary with the same number of key-value pairs, preserving insertion order, where each key k that starts with the character '*' is replaced by k[1:] (i.e., removing the single leading '*'), and all other keys remain unchanged; all values remain the same. Formally: result = d if not isinstance(d, dict) else { (k[1:] if k.startswith('*') else k) : v for k, v in d.items() }.

---

## Code Evidence

Line 5: return {(k[1:] if k.startswith("*") else k): v for k, v in d.items()}

---

## Trigger Condition

The code calls k.startswith('*') directly on the key, which fails for non-string keys like integers. The specification requires checking the string representation of the key (e.g., str(k).startswith('*')), so it should handle non-string keys gracefully. For d = {42: 'test'}, the code raises AttributeError, while the spec expects it to return {42: 'test'} unchanged.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| d | `{42: 'test'}` (a dict with an integer key) |

### Expected (spec-correct) Output

`{42: 'test'}` (the int key does not start with "*"， so the dict is returned unchanged; no crash)

### Actual (buggy) Output

`AttributeError: 'int' object has no attribute 'startswith'` (the code calls `k.startswith("*")` directly on the int key)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import _strip_star
_strip_star({42: 'test'})
# actual (buggy) output: AttributeError: 'int' object has no attribute 'startswith'
# expected (correct) output: {42: 'test'}
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on the path so `import dashboard` works
# probe is at fm_agent/bug_validation/ — go up 3 levels to repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from dashboard import _strip_star

    d = {42: 'test'}
    expected = {42: 'test'}   # spec-correct: non-string key unchanged, no crash

    try:
        actual = _strip_star(d)
        # If we got here, no exception was raised — unexpected for the buggy code
        passed = actual != expected
        if passed:
            print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
        else:
            print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
    except AttributeError:
        # The bug: k.startswith('*') fails on non-string keys like int
        actual = 'AttributeError raised'
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'AttributeError raised' | expected: {42: 'test'}
```
