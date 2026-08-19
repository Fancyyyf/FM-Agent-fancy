# Bug Report: _llm_status_style

**Source file:** `fm_agent/extracted_functions/dashboard-py/_llm_status_style.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a deterministic tuple (color, label) where color is one of the Rich-compatible style names 'green', 'yellow', or 'red' and label is a string. The mapping from (code, status) input pairs to (color, label) output pairs is a pure function: identical inputs always produce identical outputs. The label carries the input status information: it equals the string representation of whichever of code or status is non-None, or '?' if both are None, except when the outcome classifies as successful  in that case the label is forced to '200'. An outcome is classified as successful when its code equals '200' (as a string) or its status is 'success' or 'mismatch', yielding color 'green'. An outcome is classified as a client-side or format-level issue when status is 'format_error', or the string representation of the non-None input begins with the digit '4', or the string representation is exactly 'FMT', yielding color 'yellow'. All other outcomes yield color 'red'.

---

### Actual Behavior

Let t = str(code) if code is truthy else (str(status) if status is truthy else '?'). The function returns (c, l) as follows:
- If t == '200' or status in {'success', 'mismatch'}, then c = 'green' and l = '200'.
- Else if status == 'format_error' or t.startswith('4') or t == 'FMT', then c = 'yellow' and l = t.
- Else c = 'red' and l = t.
Here truthiness follows Python's boolean rules (None, False, 0, 0.0, empty string, empty list/dict are falsy; all other values are truthy). The returned label is always a string, and c is one of 'green', 'yellow', 'red'.

---

## Code Evidence

Line 2: text = str(code or status or "?")

---

## Trigger Condition

The specification requires the label to be the string representation of whichever of code or status is non-None, but the code uses truthiness with 'or', causing falsy non-None values like 0 to be ignored and fall back to '?'. For code=0 and status=None, the code returns ('red', '?') while the specification demands ('red', '0').

---

## How to trigger the bug

The function `_llm_status_style` uses Python's logical `or` operator to select the text value: `str(code or status or "?")`. In Python, `or` evaluates to the first truthy value, and the integer `0` is falsy. So when `code=0` and `status=None`, `code or status` evaluates to `None` (since `0` is falsy, it falls through), and `None or "?"` evaluates to `"?"`. The spec requires checking for *None* explicitly rather than using truthiness, so `code=0` (which is non-None) should produce text `"0"`.

### Inputs

| Parameter | Value |
|-----------|-------|
| code | `0` (integer) |
| status | `None` |

### Expected (spec-correct) Output

`('red', '0')`

### Actual (buggy) Output

`('red', '?')`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from dashboard import _llm_status_style

actual   = _llm_status_style(0, None)
expected = ("red", "0")
# actual (buggy) output: ('red', '?')
# expected (correct) output: ('red', '0')
```

---

## Probe Script

```py
"""Probe script for bug dashboard-py--_llm_status_style."""
import sys
import os
import tempfile

result = "NOT CONFIRMED"

try:
    # Use a temp directory as probe workspace (FM-Agent self-validation guard)
    probe_tmp = tempfile.mkdtemp(prefix="probe_llm_status_style_")
    # Ensure repo root is on path for the package entry-point import
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Import via public entry point: dashboard.py
    from dashboard import _llm_status_style

    # Bug trigger: code=0 (integer, non-None but falsy), status=None
    # Spec requires: text = str(code) = "0" since code is non-None
    # Buggy code: code or status or "?" -> 0 or None or "?" -> "?" because 0 is falsy
    actual = _llm_status_style(0, None)

    # Spec-correct: code=0 is non-None, so text="0", which is non-200, non-4xx, non-FMT -> color="red", label="0"
    expected = ("red", "0")

    if actual != expected:
        result = "CONFIRMED"
        print(f"CONFIRMED - actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED - actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED - actual: ('red', '?') | expected: ('red', '0')
```
