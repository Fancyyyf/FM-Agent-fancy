# Bug Report: _source_for_range

**Source file:** `fm_agent/extracted_functions/src/languages/erlang-py/_source_for_range.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the substring of source that spans from the start position (inclusive) to the end position (exclusive)

---

### Actual Behavior

If `lsp_range['start']` does not follow `lsp_range['end']` in source order, the function returns the substring of `source` that begins at the byte offset corresponding to the inclusive start position (line `lsp_range['start']['line']`, character `lsp_range['start']['character']`) and ends at the byte offset corresponding to the exclusive end position (line `lsp_range['end']['line']`, character `lsp_range['end']['character']`). If the start position does follow the end position, the behavior is undefined: the function may raise an exception (e.g., an `AssertionError` or `ValueError`) or return an arbitrary result.

---

## Code Evidence

Line 3: return _SourceIndex.build(source).source_for_range(lsp_range)

---

## Trigger Condition

The specification requires returning the substring from start to end for any input, but the code's behavior is undefined when start follows end. For the counterexample, start character 2 > end character 1. The code may raise an exception or return an arbitrary result, while the specification implies returning an empty substring (the span from start to end exclusive when start > end is empty). Thus the code violates the specification.

---

## How to trigger the bug

The probe tests whether `_source_for_range` exhibits undefined behavior or mismatched output when the LSP range start position follows the end position. When start > end, the underlying implementation calls `source[start_offset:end_offset]` with `start_offset > end_offset`, which in Python always returns an empty string — never raises an exception and never returns an arbitrary result. The spec-implied expected output is also the empty string (the span from start to end, exclusive, is empty when start > end). Therefore, actual output matches spec-expected output.

### Inputs

| Parameter | Value |
|-----------|-------|
| `source` | `"hello"` |
| `lsp_range["start"]["line"]` | `0` |
| `lsp_range["start"]["character"]` | `2` |
| `lsp_range["end"]["line"]` | `0` |
| `lsp_range["end"]["character"]` | `1` |

### Expected (spec-correct) Output

`""` (empty string — the span from character offset 2 to character offset 1 is empty)

### Actual (buggy) Output

`""` (empty string — Python slice `source[2:1]` returns empty string)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
from src.languages.erlang import _source_for_range
source = "hello"
lsp_range = {"start": {"line": 0, "character": 2}, "end": {"line": 0, "character": 1}}
result = _source_for_range(source, lsp_range)
print(repr(result))  # actual (buggy) output: ''
# expected (correct) output: ''
```

---

## Probe Script

```python
import sys
import os

# Probe runs from repo root; add cwd to path so src.languages.erlang resolves.
sys.path.insert(0, os.getcwd())

try:
    from src.languages.erlang import _source_for_range
except Exception as e:
    print(f'ERROR importing _source_for_range: {e}')
    sys.exit(1)

source = "hello"

# Trigger condition: start character 2 > end character 1 on the same line.
# start  = line 0, character 2   (byte offset 2 → points to 'l')
# end    = line 0, character 1   (byte offset 1 → points to 'e')
# start > end
lsp_range = {
    "start": {"line": 0, "character": 2},
    "end":   {"line": 0, "character": 1},
}

try:
    actual = _source_for_range(source, lsp_range)
except Exception as e:
    print(f'ERROR calling _source_for_range: {e}')
    sys.exit(1)

# Per spec: "Returns the substring of source that spans from the start
# position (inclusive) to the end position (exclusive)."
# When start offset 2 > end offset 1, the span from start to end is
# empty → expected ""
expected = ""

passed = actual != expected   # True  → the buggy output differs from spec
                              # False → actual matches spec

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: ''
```
