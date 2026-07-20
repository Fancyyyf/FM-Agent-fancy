# Bug Report: _is_test_file

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when rel_path identifies a file classified by the module as a test file
- Returns False when rel_path is not classified as a test file
- A path explicitly listed in the module-level test-file exemption set is never classified as a test file
- A path is classified as a test file when any directory component (path segments excluding the filename)
  matches the module-level test-directory naming rules
- A path is classified as a test file when its filename matches any of the module-level compiled
  test-filename regex patterns
- Test-directory matching is case-insensitive; test-filename matching follows the compiled regex rules
- The function normalizes platform path separators to forward slashes before classification

---

### Actual Behavior

The function returns a boolean with no side effects. Let norm = rel_path.replace('\\', '/'). If norm is in the set _TEST_FILE_EXEMPTIONS, the function returns False. Otherwise, let parts = norm.split('/'). If any part in parts[:-1] satisfies part.lower() in _TEST_DIR_NAMES, the function returns True. Else, let basename = parts[-1]. If there exists a pattern pat in _TEST_FILE_PATTERNS such that pat.match(basename) is not None (i.e., the pattern matches from the start of the basename), the function returns True. Otherwise, the function returns False. Formally: result = (norm  _TEST_FILE_EXEMPTIONS)  ( ( part  parts[:-1] : part.lower()  _TEST_DIR_NAMES)  ( pat  _TEST_FILE_PATTERNS : pat.match(parts[-1])  None) )  True, and False otherwise.

---

## Code Evidence

```
Line 8: for part in parts[:-1]:
Line 9:     if part.lower() in _TEST_DIR_NAMES:
Line 10:         return True
```

---

## Trigger Condition

When rel_path ends with a separator (e.g., "tests/"), the split results in parts = ['tests', ''], and parts[:-1] includes "tests". The code returns True because the directory component matches, but the path identifies a directory, not a file. The specification states the function returns True only when rel_path identifies a file, so this is a violation.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| rel_path | `"tests/"` |

### Expected (spec-correct) Output

`False` (the path identifies a directory, not a file)

### Actual (buggy) Output

`True` (the function treats "tests" as a directory component match)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import _is_test_file

# Calling with a path ending in a separator ("tests/") passes a directory, not a file.
# The spec requires False for non-file paths, but the function returns True.
result = _is_test_file("tests/")
# actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on sys.path (self-contained when run from any cwd)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from src.file_utils import _is_test_file

    # rel_path ending with separator identifies a directory, not a file
    actual   = _is_test_file("tests/")
    expected = False
    passed   = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: True | expected: False
```
