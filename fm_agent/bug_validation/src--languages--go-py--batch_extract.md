# Bug Report: batch_extract

**Source file:** `src/languages/go.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a dict mapping absolute file paths to lists of (func_name, body_text) tuples for all Go source files in proj_dir when a CodeGraph index for the project is available. Returns an empty dict when CodeGraph initialization fails or is not available for the project. Each key is an absolute filepath string; each value is a list of 2-tuples whose first element is a function name and second element is the function body text.

---

### Actual Behavior

If the call to CodeGraphExtractor.from_proj_dir(proj_dir) raises an exception, the function batch_extract terminates abnormally with that exception. If no exception occurs, let cg = CodeGraphExtractor.from_proj_dir(proj_dir). Then the function returns: if cg is None, the value {} (empty dictionary); otherwise, the value cg.get_functions_by_file("go", proj_dir), which is a dictionary mapping absolute file paths (str) to lists of (func_name, body) tuples for all Go source files under the project root. Formally: ( Exception)  ((cg = None)  result = {})  ((cg  None)  result = cg.get_functions_by_file("go", proj_dir)  k,v  result: isinstance(k, str)  isabs(k)  isinstance(v, list)  t  v: isinstance(t, tuple)  len(t)=2).

---

## Code Evidence

Line 3: cg = CodeGraphExtractor.from_proj_dir(proj_dir)

---

## Trigger Condition

The specification requires returning an empty dict when CodeGraph initialization fails, which includes any exception from from_proj_dir. The code directly calls from_proj_dir without exception handling, so if it raises (e.g., FileNotFoundError for an invalid path), batch_extract propagates the exception instead of returning {}. This violates the specification.

---

## How to trigger the bug

The `batch_extract` function in `src/languages/go.py` calls `CodeGraphExtractor.from_proj_dir(proj_dir)` without any `try/except` block. `from_proj_dir` internally calls `os.path.join(proj_dir, ".codegraph", "codegraph.db")`, which raises `TypeError` when `proj_dir` is `None` (not a string path). This exception propagates through `batch_extract` instead of being caught and returning an empty dict `{}`.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | None |

### Expected (spec-correct) Output

`{}` (empty dictionary)

### Actual (buggy) Output

`TypeError: expected str, bytes or os.PathLike object, not NoneType`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.go import batch_extract

# The spec requires returning {} when CodeGraph initialization fails.
# Passing None forces os.path.join inside from_proj_dir to raise TypeError,
# which batch_extract does not catch.
try:
    result = batch_extract(None)
    print(f"result: {result}")
except TypeError as e:
    print(f"TypeError raised: {e}")
    # actual (buggy) output: TypeError raised: expected str, bytes or os.PathLike object, not NoneType
    # expected (correct) output: result: {}
```

---

## Probe Script

```python
"""Probe script for bug: batch_extract does not catch exceptions from from_proj_dir.

Spec claim: Returns an empty dict when CodeGraph initialization fails.
Actual: If from_proj_dir raises, batch_extract propagates the exception.

Trigger: Pass an invalid type (None) as proj_dir to force os.path.join to raise TypeError
inside CodeGraphExtractor.from_proj_dir.
"""

import os
import sys

# Add repo root to Python path so `src.languages.go` is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.languages.go import batch_extract

    # from_proj_dir calls os.path.join(proj_dir, ".codegraph", "codegraph.db")
    # Passing None forces os.path.join to raise TypeError
    result = batch_extract(None)
    # If we reach here, no exception was raised — the function handled it
    print(f"NOT CONFIRMED — batch_extract(None) returned: {result!r} (no exception raised)")
except TypeError as e:
    # Bug confirmed: exception propagated instead of returning {}
    print(f"CONFIRMED — batch_extract(None) raised TypeError instead of returning {{}}: {e}")
except Exception as e:
    # Any other exception propagating is also a violation
    print(f"CONFIRMED — batch_extract(None) raised {type(e).__name__} instead of returning {{}}: {e}")
```

### Probe Output

```
CONFIRMED — batch_extract(None) raised TypeError instead of returning {}: expected str, bytes or os.PathLike object, not NoneType
```
