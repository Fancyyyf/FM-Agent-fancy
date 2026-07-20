# Bug Report: _http_status_from_exc

**Source file:** `src/llm_client.py` (line 156)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- If exc is an instance of urllib.error.HTTPError, returns the integer HTTP status code stored on exc
- If exc is not an instance of urllib.error.HTTPError, returns None
- Never raises an exception regardless of input

---

### Actual Behavior

The function returns the value of exc.code if exc is an instance of urllib.error.HTTPError; otherwise, it returns None. No side effects occur, and no exceptions are raised. Formal: (isinstance(exc, urllib.error.HTTPError)  result = exc.code)  (isinstance(exc, urllib.error.HTTPError)  result = None)

---

## Code Evidence

```
Line 158: if isinstance(exc, urllib.error.HTTPError):
Line 159:     return exc.code
```

---

## Trigger Condition

The function unconditionally accesses exc.code for any HTTPError instance. If the 'code' attribute has been removed (e.g., via deletion), this raises AttributeError, which violates the specification that the function must never raise an exception regardless of input.

---

## How to trigger the bug

An `urllib.error.HTTPError` instance with its `code` attribute deleted passes the `isinstance` check at line 158 but causes `exc.code` at line 159 to raise `AttributeError`. The spec requires the function to never raise, but it does.

### Inputs

| Parameter | Value |
|-----------|-------|
| exc | `urllib.error.HTTPError('http://example.com', 404, 'Not Found', {}, None)` with `code` attribute deleted via `del exc.code` |

### Expected (spec-correct) Output

`None` (the function should gracefully handle the missing `code` attribute without raising)

### Actual (buggy) Output

`AttributeError` raised: `'_io.BytesIO' object has no attribute 'code'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import urllib.error
from src.llm_client import _http_status_from_exc

exc = urllib.error.HTTPError('http://example.com', 404, 'Not Found', {}, None)
del exc.code
_http_status_from_exc(exc)
# actual (buggy) output: AttributeError: '_io.BytesIO' object has no attribute 'code'
# expected (correct) output: None
```

---

## Probe Script

```python
"""Probe script for bug: _http_status_from_exc raises AttributeError when code attr deleted."""
import sys
import os
import urllib.error

# Ensure the repo root is on sys.path so `src` package can be imported
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.llm_client import _http_status_from_exc

# Create an HTTPError and delete its 'code' attribute
exc = urllib.error.HTTPError('http://example.com', 404, 'Not Found', {}, None)
del exc.code

# Spec requires: Never raises an exception regardless of input
# Actual behavior: accesses exc.code unconditionally, so del exc.code → AttributeError
bug_confirmed = False
try:
    result = _http_status_from_exc(exc)
    # No exception raised — spec satisfied (bug NOT reproduced)
    print(f'NOT CONFIRMED — function returned {result!r} without raising')
except AttributeError as e:
    # Bug reproduced: spec says never raise, but AttributeError was raised
    bug_confirmed = True
    print(f'CONFIRMED — AttributeError raised: {e} | Spec requires: never raise regardless of input')
except Exception as e:
    print(f'ERROR: unexpected exception: {type(e).__name__}: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — AttributeError raised: '_io.BytesIO' object has no attribute 'code' | Spec requires: never raise regardless of input
```
