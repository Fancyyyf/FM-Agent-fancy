# Bug Report: _llm_code_for_event

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/dashboard-py/_llm_code_for_event.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a short display code string. Status values indicating successful matching or operation completion yield the code '200'. Status values indicating a malformed or unparseable result yield the code 'FMT'. Status values indicating a general error yield the code 'ERR'. For any other truthy status value, returns the status value unchanged. When status is falsy, returns '?'.

---

### Actual Behavior

Natural language: The function returns a string code based on the input status. If status is 'success' or 'mismatch', the return value is '200'. If status is 'format_error', the return value is 'FMT'. If status is 'error', the return value is 'ERR'. Otherwise, if status is truthy (non-empty string), the return value is status itself; if status is falsy (e.g., None or empty string), the return value is '?'. Formal logic: result = (if status in {'success', 'mismatch'} then '200' else if status == 'format_error' then 'FMT' else if status == 'error' then 'ERR' else (status or '?')).

---

## Code Evidence

Line 6: if status == "error":

---

## Trigger Condition

The specification requires that any status value indicating a general error return 'ERR'. The input 'ERROR' clearly indicates a general error, but the code only checks for the exact lowercase string 'error', so it falls through and returns 'ERROR' unchanged, violating the specification.

---

## How to trigger the bug

The `_llm_code_for_event` function performs an exact case-sensitive comparison against the string `"error"`. When an event carries a status like `"ERROR"` (uppercase), the check on line 6 fails and the function falls through to `return status or "?"`, returning the input `"ERROR"` unchanged. The specification requires that *any* status value indicating a general error yield `"ERR"` — case-insensitive matching is implied because error statuses may arrive in various capitalizations from different sources.

### Inputs

| Parameter | Value |
|-----------|-------|
| status | `"ERROR"` |

### Expected (spec-correct) Output

`"ERR"`

### Actual (buggy) Output

`"ERROR"`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from dashboard import _llm_code_for_event
result = _llm_code_for_event("ERROR")
print(result)
# actual (buggy) output: 'ERROR'
# expected (correct) output: 'ERR'
```

---

## Probe Script

```python
import sys
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

try:
    from dashboard import _llm_code_for_event
except Exception as e:
    print(f"ERROR: failed to import dashboard: {e}")
    sys.exit(1)

actual = None
passed = False

try:
    # The spec requires any general error status (including 'ERROR' in any case)
    # to return 'ERR'. The code only checks for exact lowercase 'error',
    # so 'ERROR' falls through and returns 'ERROR' unchanged.
    actual = _llm_code_for_event("ERROR")
    expected = "ERR"
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
CONFIRMED — actual: 'ERROR' | expected: 'ERR'
```
