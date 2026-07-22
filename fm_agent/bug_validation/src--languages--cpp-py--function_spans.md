# Bug Report: function_spans

**Source file:** `src/languages/cpp-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when a codegraph backend is unavailable or does not index the file, signaling the caller to fall back to regex-based extraction
- Otherwise returns a list of (name, start_idx, end_idx) tuples, each identifying one function in the file by its name and the range of source lines it occupies
- In every returned tuple, start_idx and end_idx are 0-indexed inclusive line indices
- The returned list covers every function that the codegraph backend detects in the file

---

### Actual Behavior

After execution, the function either propagates any exception raised by `CodeGraphExtractor.from_proj_dir(proj_dir)` or returns a value.  If no exception occurs, the return value is determined as follows: let `cg = CodeGraphExtractor.from_proj_dir(proj_dir)`. If `cg` is falsy (e.g., `None`, `False`), the function returns `None`. Otherwise, let `spans = cg.get_function_spans('cpp', filepath)`. If `spans` is `None`, the function returns `None`; otherwise it returns the list `spans`, which is a nonempty list of 3tuples `(name: str, start: int, end: int)`. Each tuple describes a function definition found in the given C++ source file, with `start` and `end` being 0indexed inclusive line numbers. The function does not modify any external state.  Formally, let `R` denote the outcome (exception or return value), `E_from` the event that `CodeGraphExtractor.from_proj_dir(proj_dir)` raises an exception.  Then: (E_from  R = that exception)  (E_from  cg is falsy  R = None)  (E_from  cg is truthy  (spans = cg.get_function_spans('cpp', filepath)  (spans = None  R = None)  (spans  None  R = spans  spans is a list of tuples each of the form (string, int, int) with semantics as stated))).

---

## Code Evidence

Line 7: cg = CodeGraphExtractor.from_proj_dir(proj_dir)
Line 8: return cg.get_function_spans("cpp", filepath) if cg else None

---

## Trigger Condition

The function does not handle exceptions from CodeGraphExtractor.from_proj_dir. When proj_dir is an invalid directory, from_proj_dir may raise an exception (e.g., FileNotFoundError) instead of returning a falsy value. The specification requires returning None when the codegraph backend is unavailable, so the caller can fall back to regex extraction. By propagating the exception, the code violates this specification for any invalid proj_dir.

---

## How to trigger the bug

Passing `None` as `proj_dir` causes `CodeGraphExtractor.from_proj_dir(None)` to call `os.path.abspath(None)`, which raises `TypeError: expected str, bytes or os.PathLike object, not NoneType`. The specification requires returning `None` to signal the caller to fall back to regex-based extraction, but the exception propagates uncaught.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `None` |
| filepath | `"dummy.cpp"` |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`TypeError: expected str, bytes or os.PathLike object, not NoneType` (propagated as an unhandled exception)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.cpp import function_spans

# Raises TypeError instead of returning None as the spec requires
function_spans(None, "dummy.cpp")
# actual (buggy) output: TypeError: expected str, bytes or os.PathLike object, not NoneType
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe script for bug: src--languages--cpp-py--function_spans

Bug: function_spans() does not handle exceptions from CodeGraphExtractor.from_proj_dir().
The specification requires returning None when the codegraph backend is unavailable,
but exceptions propagate instead of being caught.

Trigger: proj_dir=None causes os.path.abspath(None) in from_proj_dir() to raise TypeError.
"""

import sys
import os

# Ensure the repo root is on sys.path so src.languages.cpp is importable
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.languages.cpp import function_spans
except ImportError as e:
    print(f"ERROR: Could not import function_spans: {e}")
    sys.exit(1)

# --- Test: proj_dir=None should cause an exception that the spec says must be caught ---
error_caught = None
actual = None

try:
    actual = function_spans(None, "dummy.cpp")
except TypeError as e:
    error_caught = f"TypeError: {e}"
except Exception as e:
    error_caught = f"{type(e).__name__}: {e}"

expected = None  # Spec: "Returns None when a codegraph backend is unavailable"

if error_caught is not None:
    # Exception propagated → bug confirmed (spec says return None, not raise)
    print(f"CONFIRMED — exception propagated: {error_caught} | expected: {expected!r}")
elif actual == expected:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
else:
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
```

### Probe Output

```
CONFIRMED — exception propagated: TypeError: expected str, bytes or os.PathLike object, not NoneType | expected: None
```
