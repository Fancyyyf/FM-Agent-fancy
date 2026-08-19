# Bug Report: function_spans

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/languages/go-py/function_spans.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When the CodeGraph backend can index the specified Go source file, returns a list of (name, start_idx, end_idx) tuples, one tuple per function defined in the file. name is the canonicalized function name, and start_idx and end_idx are 0-indexed inclusive line indices marking the function's span. When the CodeGraph backend is unavailable or does not index the file, returns None.

---

### Actual Behavior

If the function completes normally, the return value is either None or a list of tuples. The return value is None if and only if the CodeGraph index is unavailable (CodeGraphExtractor.from_proj_dir(proj_dir) returns None) or the file is not indexed by the backend (get_function_spans('go', filepath) returns None). Otherwise, the return value is a list of (name, start_idx, end_idx) tuples, where name is a string and start_idx, end_idx are inclusive 0based line indices of the function definition; the list contains one such tuple for each function found in the file (the list may be empty if the file contains no functions). No side effects are caused beyond internal state of a transient CodeGraphExtractor instance. Formal post-condition:
let cg = CodeGraphExtractor.from_proj_dir(proj_dir) in
  (cg = None  ret = None)
   (cg  None  ret = cg.get_function_spans("go", filepath))
   (ret  None  (ret is list   e  ret : e = (name, start, end)  name is str  start, end are ints  0  start  end))
   (ret = None  (cg = None  cg.get_function_spans("go", filepath) = None)).

---

## Code Evidence

Line 8: return cg.get_function_spans("go", filepath) if cg else None

---

## Trigger Condition

The code uses 'if cg' to test whether the CodeGraphExtractor instance was obtained, but this will evaluate to False for a non-None instance that is falsy (e.g., due to a custom __bool__). In such a case, the function returns None even though the backend is available and can index the file, violating the specification which requires a non-None list when the backend can index the file.

---

## How to trigger the bug

The probe attempted to reproduce the bug by checking whether the `CodeGraphExtractor` class has a custom `__bool__` method and whether `from_proj_dir()` can return a non-None but falsy value. Neither condition is met.

### Inputs

| Parameter | Value |
|-----------|-------|
| proj_dir | `/nonexistent/proj/dir` |
| filepath | (not called — the check is on `from_proj_dir` return value) |

### Expected (spec-correct) Output

`None` (when no codegraph index exists) or a list of tuples (when the index exists).

### Actual (buggy) Output

The `if cg` check behaves identically to `if cg is not None` in this codebase because:
- `CodeGraphExtractor` has no custom `__bool__` — all instances are truthy.
- `from_proj_dir()` only returns either a `CodeGraphExtractor` instance (truthy) or `None` (falsy).

Therefore, `if cg` is functionally equivalent to `if cg is not None`, and the bug cannot be triggered.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.codegraph import CodeGraphExtractor

# Verify no custom __bool__ on CodeGraphExtractor
has_custom_bool = '__bool__' in CodeGraphExtractor.__dict__
print(f"Has custom __bool__: {has_custom_bool}")

# Verify instance truthiness
cg = CodeGraphExtractor("/nonexistent/path/to/codegraph.db")
print(f"Instance is truthy: {bool(cg)}")

# Verify from_proj_dir returns only instance or None
result = CodeGraphExtractor.from_proj_dir("/no/such/project")
print(f"from_proj_dir returns: {type(result).__name__}")

# actual output: Has custom __bool__: False
# actual output: Instance is truthy: True
# actual output: from_proj_dir returns: NoneType
```

---

## Probe Script

```python
"""Probe for bug src--languages--go-py--function_spans.

Tests whether CodeGraphExtractor instances can be falsy (custom __bool__),
which would cause `if cg` to differ from `if cg is not None` and violate
the specification.
"""
import sys
import os
import tempfile
import shutil

# Do NOT chdir before imports — that would break `from src.*` resolution.
# Workspace I/O uses temp dir set up after imports.

passed = False

try:
    # Import through the public package entry point
    from src.languages.codegraph import CodeGraphExtractor
    from src.languages.go import function_spans
except Exception as e:
    print(f'ERROR (import): {e}')
    sys.exit(1)

# Setup a fresh temp workspace for any fixture I/O (as required by the probe spec)
tmpdir = tempfile.mkdtemp(prefix="probe_fs_")

try:
    # Verify CodeGraphExtractor has no custom __bool__ that could be falsy
    has_custom_bool = '__bool__' in CodeGraphExtractor.__dict__

    # Instantiate with a non-existent db path — the constructor just stores it
    cg = CodeGraphExtractor("/nonexistent/path/to/codegraph.db")

    # Core check: is the instance truthy?
    truthy = bool(cg)                   # Python's __bool__
    is_not_none = cg is not None        # identity check

    # The spec requires `if cg` and `if cg is not None` to be equivalent
    # for this code. They differ ONLY if an instance is non-None but falsy.
    eq_result = bool(cg if truthy else None) == bool(cg if is_not_none else None)

    # Also verify from_proj_dir only returns instance or None
    result_none = CodeGraphExtractor.from_proj_dir("/nonexistent/proj/dir")
    is_none = result_none is None

    # The bug can only manifest if:
    #   - from_proj_dir returns a non-None, falsy object, OR
    #   - CodeGraphExtractor has a custom __bool__ returning False
    # Neither condition holds.

    if has_custom_bool:
        bug_possible = f"CodeGraphExtractor HAS custom __bool__ = {CodeGraphExtractor.__bool__}"
    else:
        bug_possible = "CodeGraphExtractor has NO custom __bool__"

    # All conditions for the bug to be confirmed must be true
    # Bug: if cg is non-None but falsy, function returns None incorrectly
    # For this to happen: instance must exist AND bool(instance) must be False
    can_trigger = (not is_none) and (not truthy)  # non-None but falsy

    if can_trigger:
        print("CONFIRMED — CodeGraphExtractor instance is non-None but falsy.")
    else:
        print(f"NOT CONFIRMED — {bug_possible}. "
              f"from_proj_dir on missing db returns: {type(result_none).__name__} "
              f"(is None: {is_none}). Instance truthy: {truthy}, "
              f"is not None: {is_not_none}. "
              f"'if cg' equals 'if cg is not None': {eq_result}")

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
finally:
    # Clean up the temp workspace
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Probe Output

```
NOT CONFIRMED — CodeGraphExtractor has NO custom __bool__. from_proj_dir on missing db returns: NoneType (is None: True). Instance truthy: True, is not None: True. 'if cg' equals 'if cg is not None': True
```
