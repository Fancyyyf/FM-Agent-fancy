# Bug Report: _is_path_function_label

**Source file:** `src/call_graph_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True when label contains the substring '::', the substring before the last '::' contains the character '/', and the final POSIX-path component of that substring (the portion following the last '/') contains the character '.'. Returns False otherwise.

---

### Actual Behavior

The function returns a boolean. It returns True if and only if the string `label` contains '::' and the substring before the last occurrence of '::' contains '/' and the last component of that substring when treated as a Posix path (via `PurePosixPath`) contains a period ('.'). Otherwise it returns False. No side effects occur and no exceptions are raised. Formally: let `s = label`, `k = s.rfind('::')`. If `k == -1`, the result is `False`. Otherwise, let `p = s[:k]`; the result is `True` iff `'/' in p` and `'.' in PurePosixPath(p).name`.

---

## Code Evidence

Line 4: path, _func = label.rsplit("::", 1)
Line 5: return "/" in path and "." in PurePosixPath(path).name

---

## Trigger Condition

The specification requires checking the substring after the last '/' literally, which is empty for a trailing slash. The code uses PurePosixPath(path).name, which strips trailing slashes and returns the last nonempty component. For label='a/b.c/::func', the substring before '::' is 'a/b.c/', its final POSIXpath component per spec is '' (no '.'), so spec returns False. The code returns True because PurePosixPath('a/b.c/').name is 'b.c', which contains '.'. Thus a violation occurs.

---

## How to trigger the bug

The bug is exercised through the public API `normalize_fqn_label()`, which internally calls `_is_path_function_label()`. When given a label where the substring before `::` ends with a trailing slash (e.g., `a/b.c/::func`), the spec requires the function to return `False` because the final POSIX-path component after the last `/` is the empty string `""`, which does not contain `"."`. However, the code uses `PurePosixPath(path).name`, which strips the trailing slash and returns `b.c` — a non-empty component that contains `"."` — so the code returns `True`, causing `normalize_fqn_label()` to incorrectly attempt path normalization.

### Inputs

| Parameter | Value |
|-----------|-------|
| label | `a/b.c/::func` |

### Expected (spec-correct) Output

`"a/b.c/::func"` (unchanged — not recognized as a path-function label because final POSIX-path component `""` has no `"."`)

### Actual (buggy) Output

`"a::b-c::func"` (incorrectly normalized as a path-function label)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.call_graph_edges import normalize_fqn_label

label = "a/b.c/::func"
actual = normalize_fqn_label(label)
expected = "a/b.c/::func"
# actual (buggy) output: 'a::b-c::func'
# expected (correct) output: 'a/b.c/::func'
```

---

## Probe Script

```python
"""Probe for _is_path_function_label bug: PurePosixPath strips trailing slash,
making the final path component non-empty when the spec requires it to be empty."""

import sys
import os

# Ensure repo root is on the import path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.call_graph_edges import normalize_fqn_label

    label = "a/b.c/::func"

    # Spec: the final POSIX-path component after the last '/' is '' (empty),
    # which does NOT contain '.', so _is_path_function_label should return False
    # and normalize_fqn_label should return the label unchanged.
    expected = "a/b.c/::func"

    # Actual: PurePosixPath('a/b.c/').name returns 'b.c', which contains '.',
    # so the function incorrectly treats it as a path-function label and normalizes it.
    actual = normalize_fqn_label(label)

    # Bug reproduced if actual != expected
    bug_confirmed = actual != expected

    if bug_confirmed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'a::b-c::func' | expected: 'a/b.c/::func'
```
