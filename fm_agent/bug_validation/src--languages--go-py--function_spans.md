# Bug Report: function_spans

**Source file:** `src/languages/go-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of (function_name, start_line, end_line) tuples for every
    top-level function definition found in the file at filepath.
  - start_line and end_line are 0-indexed and inclusive.
  - The returned list is ordered by function occurrence within the file.
  - Returns None when the codegraph backend is unavailable or does not index
    the file at filepath.

---

### Actual Behavior

After the function call, either an exception was raised (due to an error in `CodeGraphExtractor.from_proj_dir(proj_dir)` or, if that succeeded and returned a truthy extractor `cg`, from `cg.get_function_spans("go", filepath)`), or the function returned a value. If it returned, then `cg = CodeGraphExtractor.from_proj_dir(proj_dir)` (without raising) and: if `cg` is falsy (i.e., `None`), the return value is `None`; otherwise, the return value is the list of `(name, start_idx, end_idx)` tuples produced by `cg.get_function_spans("go", filepath)` (which also completed without exception). Format: formal logic: ( E : Exception) ( (E raised during `CodeGraphExtractor.from_proj_dir(proj_dir)`)  ( cg : cg = `CodeGraphExtractor.from_proj_dir(proj_dir)` completed  cg is truthy  E raised during `cg.get_function_spans("go", filepath)`) )  ( value : (cg = `CodeGraphExtractor.from_proj_dir(proj_dir)` completed without exception)  ( (cg is falsy  value = None)  (cg is truthy  value = `cg.get_function_spans("go", filepath)` completed without exception) ) ).

---

## Code Evidence

Line 7: cg = CodeGraphExtractor.from_proj_dir(proj_dir)
Line 8: return cg.get_function_spans("go", filepath) if cg else None

---

## Trigger Condition

The specification requires that the function returns None when the codegraph backend is unavailable. However, if CodeGraphExtractor.from_proj_dir(proj_dir) raises an exception (e.g., because no backend can be initialized from the given directory), the code propagates that exception instead of returning None, violating the specification.

---

## How to trigger the bug

The function lacks a try/except wrapper around `CodeGraphExtractor.from_proj_dir(proj_dir)`. Any exception raised by `from_proj_dir` (or its internal `os.path.abspath` call) propagates out of `function_spans` instead of being caught and converted to a `None` return value.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `None` |
| filepath | `"some_file.go"` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`TypeError` exception raised (from `os.path.abspath(None)` inside `CodeGraphExtractor.from_proj_dir`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.go import function_spans

result = function_spans(None, "some_file.go")
# actual (buggy) output: TypeError raised
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe script for bug ID: src--languages--go-py--function_spans.

Tests whether function_spans returns None (spec-correct) or propagates an
exception (buggy) when CodeGraphExtractor.from_proj_dir raises.
"""
import sys
import os

# Ensure the project root is on sys.path so that `src` is importable.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from src.languages.go import function_spans
except ImportError as e:
    print(f'ERROR: Could not import src.languages.go: {e}')
    sys.exit(1)

actual = sentinel = object()
passed = False

# Attempt 1: Pass None as proj_dir to trigger os.path.abspath(None) -> TypeError
# inside CodeGraphExtractor.from_proj_dir. The spec requires function_spans to
# return None when the backend is unavailable, not to propagate exceptions.
try:
    actual = function_spans(None, "some_file.go")
except TypeError:
    # Bug confirmed: exception propagated instead of returning None
    passed = True
    actual = '<TypeError raised>'
except Exception as e:
    # Some other exception propagated — also a bug
    passed = True
    actual = f'<{type(e).__name__} raised: {e}>'
else:
    # No exception — function returned a value
    # The spec says it should return None when backend is unavailable
    if actual is not None:
        # Bug: returned something other than None despite backend failure
        passed = True

expected = 'None (spec-correct)'

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: '<TypeError raised>' | expected: 'None (spec-correct)'
```
