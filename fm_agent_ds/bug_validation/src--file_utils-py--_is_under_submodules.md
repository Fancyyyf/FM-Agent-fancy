# Bug Report: _is_under_submodules

**Source file:** `src/file_utils.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True when submodules is None; returns True when submodules is a non-empty list and rel_path identifies a file residing within one of the named submodule directories; returns False when submodules is a non-empty list and rel_path does not reside within any named submodule directory.

---

### Actual Behavior

If `submodules` is None, the function returns True. Otherwise, it normalizes `rel_path` by replacing all backslashes with forward slashes, then repeatedly removes any leading `"./"` prefix. It returns True exactly when this normalized path equals one of the submodule directory names in `submodules` or starts with such a name followed by `"/"`; otherwise returns False. No side effects, no exceptions. Formal logic: let `norm` be the result of `rel_path.replace('\\', '/')` followed by a loop: while `norm.startswith("./")`, `norm = norm[2:]`. Then `result = (submodules is None)  ( sub  submodules: norm = sub  norm.startswith(sub + "/"))`.

---

## Code Evidence

Line 8: return any(norm == sub or norm.startswith(sub + "/") for sub in submodules)

---

## Trigger Condition

The code uses a simple string prefix check without resolving '..', so for rel_path = 'sub/../file.txt' it incorrectly returns True, but the specification requires False because the file does not actually reside under the 'sub' directory.

---

## How to trigger the bug

The function performs naive string prefix matching (`norm.startswith(sub + "/")`) without resolving `..` (parent-directory) components in the relative path. As a result, `"sub/../file.txt"` starts with `"sub/"`, which the function treats as "inside sub", but the actual resolved path `"file.txt"` is NOT inside `"sub"`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `rel_path` | `"sub/../file.txt"` |
| `submodules` | `["sub"]` |

### Expected (spec-correct) Output

`False`

### Actual (buggy) Output

`True`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.file_utils import _is_under_submodules

result = _is_under_submodules("sub/../file.txt", ["sub"])
# actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
"""Probe for bug: _is_under_submodules does not resolve '..' in paths.

The function uses a simple string prefix check (startswith) without resolving
parent-directory references, so `sub/../file.txt` incorrectly matches submodule `sub`.
"""

import sys
import os

# Ensure repo root is on sys.path so we can import via the package entry point
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.file_utils import _is_under_submodules


def main():
    """Run the bug-confirmation tests and print CONFIRMED or NOT CONFIRMED."""
    test_cases = []

    # Test 1: submodules=None → should return True (baseline, no bug here)
    try:
        r = _is_under_submodules("anything/at/all", None)
        test_cases.append(("submodules=None → True", r, True, "baseline None check"))
    except Exception as e:
        print(f"ERROR: test 1 failed with exception: {e}")
        sys.exit(1)

    # Test 2: file properly inside submodule → should return True (baseline)
    try:
        r = _is_under_submodules("sub/real_file.txt", ["sub"])
        test_cases.append(("'sub/real_file.txt' under ['sub'] → True", r, True, "valid in-submodule path"))
    except Exception as e:
        print(f"ERROR: test 2 failed with exception: {e}")
        sys.exit(1)

    # Test 3: THE BUG — path with .. that resolves outside submodule → should be False
    try:
        r = _is_under_submodules("sub/../file.txt", ["sub"])
        test_cases.append(("'sub/../file.txt' under ['sub'] → False", r, False, "SPEC: False (resolves to 'file.txt', not under 'sub')"))
    except Exception as e:
        print(f"ERROR: test 3 failed with exception: {e}")
        sys.exit(1)

    # Test 4: file NOT in submodule → should return False (baseline)
    try:
        r = _is_under_submodules("other/thing.txt", ["sub"])
        test_cases.append(("'other/thing.txt' under ['sub'] → False", r, False, "file not under submodule"))
    except Exception as e:
        print(f"ERROR: test 4 failed with exception: {e}")
        sys.exit(1)

    # Evaluate: bug is CONFIRMED if Test 3 returned True (wrong) while Test 4 returned False (correct)
    _, r_bug, expected_bug, _ = test_cases[2]
    bug_reproduced = r_bug != expected_bug

    if bug_reproduced:
        print(f"CONFIRMED — bug reproduced: _is_under_submodules does not resolve '..'")
        for desc, actual, expected, note in test_cases:
            match = "MATCH" if actual == expected else "BUG"
            print(f"  [{match}] {desc}: actual={actual!r}, expected={expected!r} | {note}")
    else:
        print(f"NOT CONFIRMED — all results matched expected:")
        for desc, actual, expected, note in test_cases:
            print(f"  [PASS] {desc}: {actual!r}")


if __name__ == "__main__":
    main()
```

### Probe Output

```
CONFIRMED — bug reproduced: _is_under_submodules does not resolve '..'
  [MATCH] submodules=None → True: actual=True, expected=True | baseline None check
  [MATCH] 'sub/real_file.txt' under ['sub'] → True: actual=True, expected=True | valid in-submodule path
  [BUG] 'sub/../file.txt' under ['sub'] → False: actual=True, expected=False | SPEC: False (resolves to 'file.txt', not under 'sub')
  [MATCH] 'other/thing.txt' under ['sub'] → False: actual=False, expected=False | file not under submodule
```
