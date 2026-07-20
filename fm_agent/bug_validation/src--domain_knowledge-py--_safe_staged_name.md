# Bug Report: _safe_staged_name

**Source file:** `src/domain_knowledge.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a filename string that was not present in used_names before the
    call and adds it to used_names as a side effect
  - The returned filename is derived from the basename of source_path:
    characters outside [A-Za-z0-9._-] in the stem are replaced with
    underscores; the stem is then stripped of leading and trailing ".", "_",
    and "-" characters; when this produces an empty stem, the stem defaults
    to "knowledge"; the extension is lowercased
  - When the derived candidate already exists in used_names, a numeric suffix
    is appended to the stem (before the extension), starting at 2 and
    incrementing by 1 until the candidate is unique within used_names
  - Given the same source_path and an equivalent used_names set, the
    returned name is deterministic

---

### Actual Behavior

After the function executes, the return value `r` is a string satisfying:
- `r` was not present in `used_names` upon entry (`r  used_names_old`), and after the call `r  used_names` with `used_names = used_names_old  {r}`.
- `r` is constructed from `source_path` as follows: let `basename = os.path.basename(source_path)`, `(stem0, ext0) = os.path.splitext(basename)`, `stem = (re.sub(r'[^A-Za-z0-9._-]+', '_', stem0).strip('._-') or 'knowledge')`, `ext = ext0.lower()`. Then either:
  (1) `stem + ext  used_names_old` and `r = stem + ext`;
  or (2) there exists an integer `k  2` such that ` j  {2, , k-1}: stem + '_' + str(j) + ext  used_names_old`, and `stem + '_' + str(k) + ext  used_names_old`, and `r = stem + '_' + str(k) + ext`.
No other side effects occur; the function always returns a value.

---

## Code Evidence

Line 12: candidate = f"{stem}_{index}{ext}"

---

## Trigger Condition

The specification requires a numeric suffix (i.e., only digits) to be appended to the stem when a candidate exists. The code inserts an underscore before the number, producing e.g., 'test_2.txt' instead of the required 'test2.txt'.

---

## How to trigger the bug

The function `_safe_staged_name` (line 88 of `src/domain_knowledge.py`) appends an underscore before the disambiguation number on line 100: `candidate = f"{stem}_{index}{ext}"`. The specification requires a plain numeric suffix (e.g., `test2.txt`), but the code produces `test_2.txt`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `source_path` | `"/some/absolute/path/to/test.txt"` |
| `used_names` | `{"test.txt"}` |

### Expected (spec-correct) Output

`"test2.txt"`

### Actual (buggy) Output

`"test_2.txt"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.domain_knowledge import _safe_staged_name

source_path = "/some/absolute/path/to/test.txt"
used_names = {"test.txt"}

actual = _safe_staged_name(source_path, used_names)
# actual (buggy) output: 'test_2.txt'
# expected (correct) output: 'test2.txt'
```

---

## Probe Script

```python
"""Probe script for bug: _safe_staged_name — underscore before numeric suffix."""

import sys

try:
    from src.domain_knowledge import _safe_staged_name

    # Trigger: base candidate "test.txt" already in used_names → disambiguation path
    source_path = "/some/absolute/path/to/test.txt"
    used_names = {"test.txt"}

    actual = _safe_staged_name(source_path, used_names)

    # Spec says: "numeric suffix is appended" → should be "test2.txt"
    # Buggy code produces: "test_2.txt" (underscore before number)
    expected_spec = "test2.txt"
    expected_buggy = "test_2.txt"

    if actual == expected_buggy:
        print(
            f"CONFIRMED — actual: {actual!r} | spec-expected: {expected_spec!r}"
        )
    elif actual == expected_spec:
        print(
            f"NOT CONFIRMED — actual matched spec: {actual!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected actual: {actual!r}"
            f" | spec-expected: {expected_spec!r}"
            f" | buggy-expected: {expected_buggy!r}"
        )

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'test_2.txt' | spec-expected: 'test2.txt'
```
