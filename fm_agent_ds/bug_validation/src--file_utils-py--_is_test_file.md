# Bug Report: _is_test_file

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/file_utils-py/_is_test_file.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Treats '/' and '\' as equivalent path separators. Returns False when the normalized path belongs to the exemption set. Otherwise, returns True when any directory component (all path segments except the filename) matches a recognized test-directory name, or when the filename matches a recognized test-file naming pattern. Returns False when none of these conditions is satisfied.

---

### Actual Behavior

The function _is_test_file returns a boolean. After normalizing rel_path by replacing any backslashes with forward slashes, the result is assigned to norm_path. If norm_path is present in the global set _TEST_FILE_EXEMPTIONS, the function immediately returns False. Otherwise, the path is split into parts by '/'. If any directory component (i.e., any part excluding the last) in lower case is a member of the global set _TEST_DIR_NAMES, the function returns True. If none match, the filename (the last part) is tested against each compiled pattern in _TEST_FILE_PATTERNS; if any pattern matches the filename, the function returns True. If none of these conditions are met, the function returns False. The function has no side effects. Formally: let norm_path = rel_path.replace('\\', '/'), parts = norm_path.split('/'). Then result = (norm_path  _TEST_FILE_EXEMPTIONS)  (( part  parts[:-1] such that part.lower()  _TEST_DIR_NAMES)  ( pat  _TEST_FILE_PATTERNS such that pat.match(parts[-1]) is not None)).

---

## Code Evidence

Line 9: if part.lower() in _TEST_DIR_NAMES:

---

## Trigger Condition

The code lowercases directory components before checking set membership, but the specification does not require case-insensitive matching. This causes a false negative when a recognized test-directory name contains uppercase letters, as the lowercased version will not be found in the set.

---

## How to trigger the bug

The specification implies case-sensitive matching against `_TEST_DIR_NAMES` — a directory component must match the set entry verbatim. The code lowercases the directory component before the set lookup (`part.lower() in _TEST_DIR_NAMES`), making the check case-insensitive. When `_TEST_DIR_NAMES` contains all-lowercase entries (the default), passing a path with an uppercased variant (e.g., `"Tests"` for `"tests"`) causes the code to return `True` while the specification requires `False`.

### Inputs

| Parameter | Value |
|-----------|-------|
| rel_path | `"a/Tests/file.py"` |

### Expected (spec-correct) Output

`False` — The directory component `"Tests"` does not match any entry in the all-lowercase `_TEST_DIR_NAMES` set under case-sensitive comparison.

### Actual (buggy) Output

`True` — The code lowercases `"Tests"` to `"tests"`, which is present in `_TEST_DIR_NAMES`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import _is_test_file

result = _is_test_file("a/Tests/file.py")
print(result)
# actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so 'from src.file_utils import ...' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.file_utils import _is_test_file

    # The spec says: "Returns True when any directory component matches a recognized
    # test-directory name."  _TEST_DIR_NAMES = {"test", "tests", ...} (all lowercase).
    # The spec implies case-sensitive matching — "Tests" ∉ _TEST_DIR_NAMES.
    #
    # The code (line 262) does: `part.lower() in _TEST_DIR_NAMES`
    # So "Tests".lower() = "tests" IS in _TEST_DIR_NAMES → returns True.
    #
    # Bug: the code lowercases before checking, making the match case-insensitive.
    # Expected: False (case-sensitive does not match)
    # Actual:   True  (code lowercases, producing case-insensitive match)

    test_path = "a/Tests/file.py"

    actual = _is_test_file(test_path)
    expected = False  # per spec — case-sensitive: "Tests" not in {"tests", ...}

    bug_reproduced = actual != expected

    if bug_reproduced:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: True | expected: False
```
