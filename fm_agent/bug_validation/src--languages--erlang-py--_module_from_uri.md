# Bug Report: _module_from_uri

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_module_from_uri.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the filename stem (final path component with its last dot-extension removed)
    of the path portion of uri
  - Percent-encoded characters in the URI path are decoded before stem extraction
  - Backslash characters in the decoded path are normalized to forward slash before stem
    extraction; path components are interpreted using POSIX semantics
  - Query, fragment, and scheme components of the URI, if present, do not affect the
    result
  - The returned string contains no instances of the double-underscore sequence ("__")
  - The returned string is non-empty

---

### Actual Behavior

The function returns a string `result` such that `result` equals `PurePosixPath(unquote(urlparse(uri).path).replace('\\', '/')).stem`. No exceptions are raised. Formally: `result = PurePosixPath(unquote(urlparse(uri).path).replace('\\', '/')).stem` and `isinstance(result, str)`.

---

## Code Evidence

Line 3: return PurePosixPath(path.replace("\\", "/")).stem

---

## Trigger Condition

The code extracts the stem without ensuring conformance to the specification's double-underscore and non-empty restrictions. For the counterexample 'http://example.com/__init__.py', the path is '/__init__.py' and PurePosixPath.stem returns '__init__', which contains '__', violating the requirement that the result contains no double-underscore sequence.

---

## How to trigger the bug

Provide a URI whose path component, after removing the file extension, yields a stem containing `__` (double underscore). The function passes the path through `PurePosixPath.stem` without sanitizing for `__` sequences, so any stem containing `__` is returned verbatim, violating the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| uri | `http://example.com/__init__.py` |

### Expected (spec-correct) Output

A string containing no `__` sequence (e.g., `init` if `__` were stripped from the stem).

### Actual (buggy) Output

`__init__`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _module_from_uri
result = _module_from_uri("http://example.com/__init__.py")
print(result)
# actual (buggy) output: __init__
# expected (correct) output: <contains no "__">
```

---

## Probe Script

```python
"""Probe: Does _module_from_uri return stems containing '__'?

Spec claims the result "contains no instances of the double-underscore sequence ('__')".
Code evidence (Line 306): return PurePosixPath(path.replace("\\", "/")).stem
Trigger: uri = "http://example.com/__init__.py" → PurePosixPath.stem returns "__init__" which contains "__".
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.languages.erlang import _module_from_uri
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

uri = "http://example.com/__init__.py"

try:
    actual = _module_from_uri(uri)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# Spec requires no "__" in result. The buggy code returns "__init__" which contains "__".
contains_double_underscore = "__" in actual

if contains_double_underscore:
    print(f"CONFIRMED — result contains double-underscore: {actual!r} | spec requires no '__' in result")
else:
    print(f"NOT CONFIRMED — result has no double-underscore: {actual!r}")
```

### Probe Output

```
CONFIRMED — result contains double-underscore: '__init__' | spec requires no '__' in result
```
