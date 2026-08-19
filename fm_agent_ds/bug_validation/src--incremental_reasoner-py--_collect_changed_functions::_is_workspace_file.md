# Bug Report: _is_workspace_file

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True when rel_path, after replacing every backslash with a forward slash, equals the exact string "fm_agent" or has the prefix "fm_agent/". Returns False in all other cases, including when rel_path is empty, contains only the fm_agent directory name but with additional path components that do not form a descendant path under fm_agent/, or represents a file whose normalized path falls outside the fm_agent/ workspace tree.

---

### Actual Behavior

The function _is_workspace_file returns True if the normalized version of rel_path, obtained by replacing every backslash '\' with a forward slash '/', equals the string 'fm_agent' or starts with 'fm_agent/'; otherwise it returns False. The function has no side effects and does not modify rel_path. Formally:  rel_path  Strings, _is_workspace_file(rel_path)  (rel_path.replace('\\\\', '/') = 'fm_agent')  (rel_path.replace('\\\\', '/').startswith('fm_agent/')).

---

## Code Evidence

Line 3: return norm == "fm_agent" or norm.startswith("fm_agent/")

(Actual source: `src/incremental_reasoner.py` lines 378-380)

```python
def _is_workspace_file(rel_path):
    norm = rel_path.replace("\\", "/")
    return norm == "fm_agent" or norm.startswith("fm_agent/")
```

---

## Trigger Condition

The code uses a simple string prefix check after replacing backslashes. For the input 'fm_agent/..', normalization yields 'fm_agent/..', which starts with 'fm_agent/', so the code returns True. However, the specification requires False when the path does not form a descendant path under fm_agent/, and '..' escapes the directory, making it a nondescendant. The string prefix alone does not detect such escapes, violating the specification.

---

## How to trigger the bug

Call `_is_workspace_file` with any `rel_path` that begins with `fm_agent/` but contains `..` components that escape the workspace directory. The naive `startswith("fm_agent/")` check passes because the normalized path still starts with that prefix, despite the `..` escaping to a parent directory outside the workspace.

### Inputs

| Parameter | Value |
|-----------|-------|
| `rel_path` | `"fm_agent/.."` |
| `rel_path` | `"fm_agent/../escape.py"` |
| `rel_path` | `"fm_agent/../../outside"` |
| `rel_path` | `"fm_agent/subdir/../../../root.txt"` |
| `rel_path` | `"fm_agent\\..\\escape.rs"` (Windows backslash) |

### Expected (spec-correct) Output

`False` — These paths escape the `fm_agent/` workspace directory via `..`, so they should not be considered workspace files.

### Actual (buggy) Output

`True` — The function only checks whether the normalized path starts with `"fm_agent/"`, which all of these inputs satisfy despite the directory escape.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
# The function is a nested closure inside _collect_changed_functions (src/incremental_reasoner.py:378-380).
# Its exact logic:
def _is_workspace_file(rel_path):
    norm = rel_path.replace("\\", "/")
    return norm == "fm_agent" or norm.startswith("fm_agent/")

print(_is_workspace_file("fm_agent/.."))          # actual (buggy) output: True
# expected (correct) output: False

print(_is_workspace_file("fm_agent/../x.py"))     # actual (buggy) output: True
# expected (correct) output: False
```

---

## Probe Script

```python
"""Probe for _is_workspace_file bug: fm_agent/.. escapes the workspace but passes the prefix check.

The target function is a nested closure inside _collect_changed_functions; its exact logic is
replicated here as the smallest testable unit per the FM-Agent self-validation guard.
"""

import sys

# Exact logic from src/incremental_reasoner.py line 378-380
def _is_workspace_file(rel_path):
    norm = rel_path.replace("\\", "/")
    return norm == "fm_agent" or norm.startswith("fm_agent/")

# Expected behavior per spec:
# - True when rel_path equals "fm_agent" or starts with "fm_agent/"
# - False when path escapes the workspace (e.g. via "..")

test_cases = [
    # (rel_path, expected_per_spec, description)
    ("fm_agent", True, "exact match"),
    ("fm_agent/some_file.py", True, "descendant inside workspace"),
    ("fm_agent/nested/deep/file.c", True, "deeply nested descendant"),
    ("fm_agent\\subdir\\file.rs", True, "Windows backslash normalization"),
    ("src/main.py", False, "outside workspace entirely"),
    ("", False, "empty path"),
    ("fm", False, "partial prefix match, not fm_agent"),
    ("fm_agent/..", False, ".. escapes the workspace directory"),
    ("fm_agent/../escape.py", False, ".. escape with trailing file"),
    ("fm_agent/../../outside", False, "double .. escape"),
    ("fm_agent/subdir/../../../root.txt", False, "nested then .. escape"),
    ("fm_agent\\..\\escape.rs", False, "Windows backslash .. escape"),
]

all_passed = True
results = []

for rel_path, expected, desc in test_cases:
    try:
        actual = _is_workspace_file(rel_path)
        passed = actual == expected
        status = "PASS" if passed else "FAIL"
        results.append((status, rel_path, expected, actual, desc))
        if not passed:
            all_passed = False
    except Exception as e:
        results.append(("ERROR", rel_path, expected, str(e), desc))
        all_passed = False

# Print results
for status, rel_path, expected, actual, desc in results:
    print(f"[{status}] rel_path={rel_path!r}  expected={expected}  actual={actual}  ({desc})")

# Overall verdict: the bug is CONFIRMED if any test case that should be False returns True.
buggy_cases = [r for r in results if r[0] == "FAIL"]

if buggy_cases:
    print(f"\nCONFIRMED — {len(buggy_cases)} test case(s) expose the bug:")
    for status, rel_path, expected, actual, desc in buggy_cases:
        print(f"  rel_path={rel_path!r}: expected {expected}, got {actual} ({desc})")
else:
    print("\nNOT CONFIRMED — all test cases matched expected behavior")
```

### Probe Output

```
[PASS] rel_path='fm_agent'  expected=True  actual=True  (exact match)
[PASS] rel_path='fm_agent/some_file.py'  expected=True  actual=True  (descendant inside workspace)
[PASS] rel_path='fm_agent/nested/deep/file.c'  expected=True  actual=True  (deeply nested descendant)
[PASS] rel_path='fm_agent\\subdir\\file.rs'  expected=True  actual=True  (Windows backslash normalization)
[PASS] rel_path='src/main.py'  expected=False  actual=False  (outside workspace entirely)
[PASS] rel_path=''  expected=False  actual=False  (empty path)
[PASS] rel_path='fm'  expected=False  actual=False  (partial prefix match, not fm_agent)
[FAIL] rel_path='fm_agent/..'  expected=False  actual=True  (.. escapes the workspace directory)
[FAIL] rel_path='fm_agent/../escape.py'  expected=False  actual=True  (.. escape with trailing file)
[FAIL] rel_path='fm_agent/../../outside'  expected=False  actual=True  (double .. escape)
[FAIL] rel_path='fm_agent/subdir/../../../root.txt'  expected=False  actual=True  (nested then .. escape)
[FAIL] rel_path='fm_agent\\..\\escape.rs'  expected=False  actual=True  (Windows backslash .. escape)

CONFIRMED — 5 test case(s) expose the bug:
  rel_path='fm_agent/..': expected False, got True (.. escapes the workspace directory)
  rel_path='fm_agent/../escape.py': expected False, got True (.. escape with trailing file)
  rel_path='fm_agent/../../outside': expected False, got True (double .. escape)
  rel_path='fm_agent/subdir/../../../root.txt': expected False, got True (nested then .. escape)
  rel_path='fm_agent\\..\\escape.rs': expected False, got True (Windows backslash .. escape)
```
