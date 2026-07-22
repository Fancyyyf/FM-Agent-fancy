# Bug Report: _fqn_to_ident

**Source file:** `src/entry_reasoning_pipeline-py/_fqn_to_ident.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the class-qualified function identifier obtained by removing the
    path prefix up to and including the source-file component from fqn
  - A component is recognized as a source-file component when it consists of
    a non-empty base name, a hyphen, and a suffix that is a recognized
    source-file language extension
  - When fqn contains more than one source-file component, the rightmost one
    determines where the prefix ends
  - When fqn contains no source-file component, returns the last component
    of fqn unchanged
  - The returned string is non-empty

---

### Actual Behavior

Let parts = fqn.split("::"), n = len(parts). Let i be the largest index in the range [0, n-1] such that there exists an integer pos > 0 where parts[i][pos] == '-' and parts[i][pos+1:] is a key in EXT_TO_LANG. If such an i exists, then result = "::".join(parts[i+1:]) (which may be an empty string if i == n-1). Otherwise, result = parts[-1].

---

## Code Evidence

Line 15: return "::".join(parts[i + 1:])

---

## Trigger Condition

When the rightmost source-file component is the last component of the FQN, parts[i+1:] is empty, so the code returns an empty string, violating the specification requirement that the returned string is non-empty.

---

## How to trigger the bug

When an FQN has the source-file component as its final component (with no class/function qualifier after it), `parts[i+1:]` produces an empty slice, `"::".join([])` evaluates to `""`, and the function returns an empty string. The specification requires the return value to be non-empty.

### Inputs

| Parameter | Value |
|-----------|-------|
| fqn | `src::storage-cpp` |
| fqn | `storage-cpp` |

### Expected (spec-correct) Output

`"storage-cpp"` (non-empty — at minimum, the source-file component itself should be returned when it is the last component)

### Actual (buggy) Output

`""` (empty string)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.entry_reasoning_pipeline import _fqn_to_ident

# When the rightmost source-file component is the last FQN component:
result = _fqn_to_ident("src::storage-cpp")
print(repr(result))  # actual (buggy) output: ''
# expected (correct) output: 'storage-cpp'
```

---

## Probe Script

```python
"""Probe for _fqn_to_ident bug: empty string when source-file component is the last FQN component."""
import sys
import os

# Add the project root to sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.entry_reasoning_pipeline import _fqn_to_ident
except Exception as e:
    print(f"ERROR: Failed to import _fqn_to_ident: {e}")
    sys.exit(1)

# --- Test cases ---
# Test case 1: Normal - source-file is NOT the last component
#   src::storage-cpp::LocalStorage::Flush -> "LocalStorage::Flush"
actual_1 = _fqn_to_ident("src::storage-cpp::LocalStorage::Flush")
expected_1 = "LocalStorage::Flush"
assert actual_1 == expected_1, f"Test 1 failed: got {actual_1!r}, expected {expected_1!r}"

# Test case 2: Normal - source-file is NOT the last component
#   src::checkpoint-cpp::RunCheckpoint -> "RunCheckpoint"
actual_2 = _fqn_to_ident("src::checkpoint-cpp::RunCheckpoint")
expected_2 = "RunCheckpoint"
assert actual_2 == expected_2, f"Test 2 failed: got {actual_2!r}, expected {expected_2!r}"

# Test case 3: BUG - source-file IS the last component
#   src::storage-cpp -> should be non-empty per spec, but returns ""
actual_3 = _fqn_to_ident("src::storage-cpp")
expected_3 = "storage-cpp"  # spec-correct: at minimum non-empty; reasonable value
passed_3 = (actual_3 != expected_3)  # bug is confirmed if they differ

# Test case 4: BUG - single component that IS a source-file
#   storage-cpp -> should be non-empty, returns ""
actual_4 = _fqn_to_ident("storage-cpp")
expected_4 = "storage-cpp"  # spec-correct: non-empty
passed_4 = (actual_4 != expected_4)  # bug is confirmed if they differ

# Test case 5: No source-file component
#   MyClass::myMethod -> "myMethod" (fallback)
actual_5 = _fqn_to_ident("MyClass::myMethod")
expected_5 = "myMethod"
assert actual_5 == expected_5, f"Test 5 failed: got {actual_5!r}, expected {expected_5!r}"

# --- Verdict ---
bug_confirmed = passed_3 and passed_4

if bug_confirmed:
    print(f"CONFIRMED")
    print(f"  Test 3 (src::storage-cpp):        actual={actual_3!r} | expected={expected_3!r}")
    print(f"  Test 4 (storage-cpp):             actual={actual_4!r} | expected={expected_4!r}")
    print(f"  Tests 1,2,5 (no-bug cases):       all passed")
else:
    print(f"NOT CONFIRMED")
```

### Probe Output

```
CONFIRMED
  Test 3 (src::storage-cpp):        actual='' | expected='storage-cpp'
  Test 4 (storage-cpp):             actual='' | expected='storage-cpp'
  Tests 1,2,5 (no-bug cases):       all passed
```
