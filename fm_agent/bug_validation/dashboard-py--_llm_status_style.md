# Bug Report: _llm_status_style

**Source file:** `fm_agent/extracted_functions/dashboard-py/_llm_status_style.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a pair (color, label) where color is a Rich-compatible
    color name and label is a display string.
  - The label is constructed by selecting the first truthy value from
    code, status, and the string "?" in that priority order, converted
    to a string.
  - When the label is "200" or status is a completion-type status
    (indicating the operation finished), the pair is ("green", "200").
  - When status is a format-error type or the label begins with "4" or
    equals "FMT", the pair is ("yellow", label).
  - For all other code/status combinations, the pair is ("red", label).

---

### Actual Behavior

Let t = str(code) if code else (str(status) if status else "?"). Then the function returns: ("green", "200") if t == "200" or status in ("success", "mismatch"); else ("yellow", t) if status == "format_error" or t.startswith('4') or t == "FMT"; else ("red", t). Formally, for the return value r: ( (t = "200"  status  {"success", "mismatch"})  r = ("green", "200") )  ( ((t = "200"  status  {"success", "mismatch"})  (status = "format_error"  t starts with "4"  t = "FMT"))  r = ("yellow", t) )  ( ((t = "200"  status  {"success", "mismatch"})  (status = "format_error"  t starts with "4"  t = "FMT"))  r = ("red", t) ).

---

## Code Evidence

Line 3: if text == "200" or status in ("success", "mismatch"):

---

## Trigger Condition

The specification requires ('green', '200') when status is any completion-type status, but the code only checks for 'success' and 'mismatch'. For code=None and status='completed' (a valid completion status), the label becomes 'completed', and the code returns ('red', 'completed') instead of the required ('green', '200').

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| code | None |
| status | "completed" |

### Expected (spec-correct) Output

`("green", "200")`

### Actual (buggy) Output

`("red", "completed")`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import dashboard
dashboard._llm_status_style(None, "completed")
# actual (buggy) output: ("red", "completed")
# expected (correct) output: ("green", "200")
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on the import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import dashboard
    actual   = dashboard._llm_status_style(None, "completed")
    expected = ("green", "200")
    passed   = actual != expected
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: ('red', 'completed') | expected: ('green', '200')
```
