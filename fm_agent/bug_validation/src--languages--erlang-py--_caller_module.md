# Bug Report: _caller_module

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the Erlang module name derived from the file's base name by
    replacing the last occurrence of "." in the base name with "-"
  - When the base name contains no "." character, returns the base name
    unchanged
  - The result is deterministic: identical path strings always produce
    identical return values
  - The result depends only on the basename portion of path (the final path
    component after the last "/" or "\")

---

### Actual Behavior

The function returns a string that is the basename of the input path, but with the last '.' replaced by '-', unless the basename starts with '.' or contains no '.', in which case it returns the basename unchanged. In other words: let b = os.path.basename(path). If b has no '.' or b[0] == '.', then the result equals b; otherwise, let i be the index of the last '.' in b (so b[i] == '.', i > 0, and no later '.' exists), then the result is b[:i] + '-' + b[i+1:].

---

## Code Evidence

Line 370-373 in `src/languages/erlang.py`:
```python
def _caller_module(path: str) -> str:
    base = os.path.basename(path)
    dot = base.rfind(".")
    return base[:dot] + "-" + base[dot + 1 :] if dot > 0 else base
```

The condition `dot > 0` excludes the case where the last dot is at index 0 (filename starts with `.`).

---

## Trigger Condition

The specification requires replacing the last dot in the basename, regardless of its position. For basename '.hidden', the last dot is at index 0. The code's condition `dot > 0` is false, so it returns '.hidden' unchanged, but the specification would return '-hidden'. Thus the code violates the spec for any basename that starts with a dot and contains at least one dot.

---

## How to trigger the bug

Call `_caller_module` with a path whose basename starts with a dot and contains at least one dot (e.g., `/path/to/.hidden`). The function returns the basename unchanged instead of replacing the leading dot with `-`.

### Inputs

| Parameter | Value |
|-----------|-------|
| path | `/path/to/.hidden` |

### Expected (spec-correct) Output

`-hidden`

### Actual (buggy) Output

`.hidden`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _caller_module

path = "/path/to/.hidden"
result = _caller_module(path)
print(result)
# actual (buggy) output: .hidden
# expected (correct) output: -hidden
```

---

## Probe Script

```python
import sys

try:
    from src.languages.erlang import _caller_module

    # Test case: basename starts with a dot, contains at least one dot.
    # Example: "/path/to/.hidden" → basename = ".hidden"
    #   rfind(".") returns 0
    #   dot > 0 → False → returns ".hidden" (unchanged) — BUG
    #   Spec says: replace last "." with "-" → should return "-hidden"
    path = "/path/to/.hidden"
    actual = _caller_module(path)
    expected = "-hidden"
    passed = actual != expected

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: '.hidden' | expected: '-hidden'
```
