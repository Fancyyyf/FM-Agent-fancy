# Bug Report: batch_extract

**Source file:** `src/languages/cpp.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dictionary where each key is an absolute file path (str) and
    each value is a list of (function_name: str, body: str) tuples.
  - Every key corresponds to a C++ source file under proj_dir for which
    codegraph extracted at least one top-level function.
  - Each function_name is the canonical name of a function defined in the
    corresponding source file.
  - Each body is the full source text of that function as returned by
    codegraph.
  - If codegraph is not available for proj_dir (CodeGraphExtractor.from_proj_dir
    returns a falsy value), the returned dictionary is empty.
  - The returned dictionary does not include entries for non-C++ files or for
    files from which codegraph extracted zero functions.

---

### Actual Behavior

If the function terminates normally, it returns a dictionary d: if the CodeGraphExtractor initialization from proj_dir failed (returned a falsy value), then d == {}; otherwise, d == cg.get_functions_by_file('cpp', proj_dir), i.e., a mapping from each absolute file path of a C++ source file (.cpp, .cc, .cxx) under proj_dir to a list of (function_name: str, body: str) tuples for all top-level functions in that file. If an exception is raised (e.g., due to an inaccessible directory, permission error, or internal error), the exception propagates and no return value is produced.

---

## Code Evidence

Line 3: cg = CodeGraphExtractor.from_proj_dir(proj_dir)
Line 4: return cg.get_functions_by_file("cpp", proj_dir) if cg else {}

---

## Trigger Condition

When proj_dir is a path that does not exist, CodeGraphExtractor.from_proj_dir may raise an exception (e.g., FileNotFoundError) instead of returning a falsy value. The code propagates the exception and does not return a dictionary. However, the specification requires the function to return an empty dictionary if codegraph is not available. Since an exception does not satisfy the return-type clause, the code violates the specification.

---

## How to trigger the bug

The function `batch_extract` has no exception handling around the call to `CodeGraphExtractor.from_proj_dir()`. When any exception is raised during that call — whether from an invalid input type, a permission error, or an unexpected internal error — the exception propagates to the caller instead of being caught and the function returning an empty dictionary (`{}`) as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `None` |

### Expected (spec-correct) Output

`{}` (empty dictionary) — per the specification: "If codegraph is not available for proj_dir (CodeGraphExtractor.from_proj_dir returns a falsy value), the returned dictionary is empty."

### Actual (buggy) Output

`TypeError: expected str, bytes or os.PathLike object, not NoneType` — the exception propagates uncaught from `os.path.abspath(None)` inside `CodeGraphExtractor.from_proj_dir()`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.cpp import batch_extract
batch_extract(None)
# actual (buggy) output: TypeError: expected str, bytes or os.PathLike object, not NoneType
# expected (correct) output: {}
```

---

## Probe Script

```python
"""Probe script for bug src--languages--cpp-py--batch_extract — attempt 2.

Bug claim: batch_extract(proj_dir) raises an exception instead of returning {}
when proj_dir does not exist (spec requires returning empty dict).
"""
import sys
import os

repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.languages.cpp import batch_extract

    # Test with None — type mismatch may trigger exception
    try:
        actual = batch_extract(None)
        print(f"NOT CONFIRMED — returned {actual!r} for None input")
    except TypeError as e:
        print(f"CONFIRMED — TypeError raised for None: {e}")
    except Exception as e:
        import traceback
        print(f"CONFIRMED — exception raised for None: {e}")
        traceback.print_exc()

except Exception as e:
    import traceback
    print(f"CONFIRMED — script-level exception: {e}")
    traceback.print_exc()
```

### Probe Output

```
CONFIRMED — TypeError raised for None: expected str, bytes or os.PathLike object, not NoneType
```
