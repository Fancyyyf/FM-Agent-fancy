# Bug Report: _stable_user_id

**Source file:** `src/llm_client.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the value of the INJECT_ID environment variable when that variable is set and its value is non-empty
  - Returns a predefined static default value when INJECT_ID is not set or its value is empty
  - The returned string is non-empty in all cases

---

### Actual Behavior

The function returns a string. If the environment variable 'INJECT_ID' is set to a non-empty string, the return value is that string; otherwise, it is the value of `_DEFAULT_INJECT_USER_ID`. Formally: Let `v = os.environ.get('INJECT_ID')`. Then the returned value `r` satisfies `(v is not None and v != '' and r = v) or ((v is None or v == '') and r = _DEFAULT_INJECT_USER_ID)`.

---

## Code Evidence

Line 2: return os.environ.get("INJECT_ID") or _DEFAULT_INJECT_USER_ID

---

## Trigger Condition

The function relies on _DEFAULT_INJECT_USER_ID being non-empty to satisfy the requirement that the returned string is non-empty in all cases. If _DEFAULT_INJECT_USER_ID is empty or None, the function returns an empty string or None, violating the specification.

---

## How to trigger the bug

The function uses Python's `or` operator as a fallback: when `os.environ.get("INJECT_ID")` returns a falsy value (None when the env var is not set, or an empty string when it is set to empty), the `or` expression evaluates `_DEFAULT_INJECT_USER_ID`. If `_DEFAULT_INJECT_USER_ID` itself is also falsy (empty string or None), the entire expression evaluates to a falsy value, violating the specification requirement that the returned string must be non-empty in all cases.

### Inputs

| Parameter | Value |
|-----------|-------|
| `INJECT_ID` (env) | not set |
| `_DEFAULT_INJECT_USER_ID` | `""` (empty string, monkey-patched) |

### Expected (spec-correct) Output

A non-empty string (should be a hardcoded fallback that is always non-empty, or the function should raise an error).

### Actual (buggy) Output

`""` (empty string)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, ".")
import src.llm_client as llm_client

os.environ.pop("INJECT_ID", None)
llm_client._DEFAULT_INJECT_USER_ID = ""
result = llm_client._stable_user_id()
print(result)  # actual (buggy) output: '' (empty string)
# expected (correct) output: non-empty string
```

---

## Probe Script

```python
"""Probe script for bug src--llm_client-py--_stable_user_id.

Spec claim: _stable_user_id() always returns a non-empty string.
Bug: os.environ.get("INJECT_ID") or _DEFAULT_INJECT_USER_ID can return falsy
     when INJECT_ID is unset AND _DEFAULT_INJECT_USER_ID is falsy.
"""

import sys
import os

# Add repo root to sys.path so that 'src' and 'config' are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

# Ensure INJECT_ID is NOT set in the environment
os.environ.pop("INJECT_ID", None)

# Import the module via its public entry point
import src.llm_client as llm_client

try:
    # Monkey-patch _DEFAULT_INJECT_USER_ID to an empty string to trigger the bug
    llm_client._DEFAULT_INJECT_USER_ID = ""

    actual = llm_client._stable_user_id()
    # Spec requires: "The returned string is non-empty in all cases"
    # Bug is triggered if the return is falsy (empty string or None)
    bug_triggered = not actual

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_triggered:
    print(f"CONFIRMED — actual: {actual!r} | expected: non-empty string per spec")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: '' | expected: non-empty string per spec
```
