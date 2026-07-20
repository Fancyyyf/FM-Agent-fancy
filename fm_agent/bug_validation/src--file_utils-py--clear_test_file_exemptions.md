# Bug Report: clear_test_file_exemptions

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- The module-level set of exempted test-file paths is empty.
  - All paths previously registered via `add_test_file_exemption` are no longer
    exempt; subsequent test-file classification functions will apply default
    heuristics to every path.

---

### Actual Behavior

The function `clear_test_file_exemptions` is bound in the module's global scope. The set `_TEST_FILE_EXEMPTIONS` exists and retains its previous contents; none of its elements have been added or removed. Formally: (clear_test_file_exemptions  globals())  (_TEST_FILE_EXEMPTIONS  globals())  (_TEST_FILE_EXEMPTIONS = old(_TEST_FILE_EXEMPTIONS)).

---

## Code Evidence

Line 3: _TEST_FILE_EXEMPTIONS.clear()

---

## Trigger Condition

Condition A (actual behavior) states the set retains its previous contents, but specification B requires the set to be empty after the call. With the given non-empty initial state, A leaves the set non-empty, violating B.

---

## How to trigger the bug

The probe script calls `clear_test_file_exemptions()` after populating `_TEST_FILE_EXEMPTIONS` with three entries via `add_test_file_exemption()`. The function correctly calls `_TEST_FILE_EXEMPTIONS.clear()`, which empties the set in place. The bug could not be reproduced.

### Inputs

| Parameter | Value |
|-----------|-------|
| add_test_file_exemption (call 1) | `"path/to/test1.py"` |
| add_test_file_exemption (call 2) | `"path/to/test2.py"` |
| add_test_file_exemption (call 3) | `"some/other/test.py"` |
| clear_test_file_exemptions() | (no arguments) |

### Expected (spec-correct) Output

`_TEST_FILE_EXEMPTIONS` is `set()` (empty)

### Actual (buggy) Output

`_TEST_FILE_EXEMPTIONS` is `set()` (empty) — matches spec

### How to Reproduce

The claimed bug does not exist. `set.clear()` is a standard Python built-in method that reliably empties a mutable set in place. The reasoning engine appears to have produced a hallucination about the behavior of `_TEST_FILE_EXEMPTIONS.clear()`.

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import add_test_file_exemption, clear_test_file_exemptions
import src.file_utils as futils

add_test_file_exemption("path/to/test1.py")
add_test_file_exemption("path/to/test2.py")
clear_test_file_exemptions()
print(len(futils._TEST_FILE_EXEMPTIONS))  # Output: 0 — correctly emptied
```

---

## Probe Script

```python
import sys

try:
    from src.file_utils import add_test_file_exemption, clear_test_file_exemptions
    import src.file_utils as futils

    # Add some exemptions to populate the set
    add_test_file_exemption("path/to/test1.py")
    add_test_file_exemption("path/to/test2.py")
    add_test_file_exemption("some/other/test.py")

    # Verify set is non-empty before calling clear
    before = set(futils._TEST_FILE_EXEMPTIONS)
    if not before:
        print('SETUP FAILED — _TEST_FILE_EXEMPTIONS was already empty before clear')
        sys.exit(1)

    # Call clear
    clear_test_file_exemptions()

    after = futils._TEST_FILE_EXEMPTIONS

    if len(after) > 0:
        print(f'CONFIRMED — actual: {after!r} (not empty) | expected: set() (empty)')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {before!r} -> {after!r} (empty after clear)')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: {'some/other/test.py', 'path/to/test2.py', 'path/to/test1.py'} -> set() (empty after clear)
```
