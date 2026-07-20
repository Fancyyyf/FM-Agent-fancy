# Bug Report: _parse_spec_check_json

**Source file:** `src/prompts.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Raises ValueError if response is not valid JSON text
  - Raises ValueError if the parsed JSON value is not a mapping (dict)
  - Raises ValueError if the parsed mapping does not contain all of the required keys: "verdict", "counterexample", "offending_statements", "reason"
  - Raises ValueError if the "verdict" value, after conversion to uppercase, is neither "MATCH" nor "MISMATCH"
  - Raises ValueError if "counterexample" is present and not null-valued but is not a string
  - Raises ValueError if "offending_statements" is present and not null-valued but is not a string
  - Raises ValueError if "reason" is not a string value
  - For "MISMATCH" verdict: raises ValueError if any of counterexample, offending_statements, or reason is empty or consists only of whitespace; otherwise returns a tuple (True, offending_statements_with_leading_trailing_whitespace_removed, reason_with_whitespace_removed, data) where data is the parsed dict with verdict uppercased, counterexample set to the stripped value, offending_statements set to the stripped value, and reason set to the stripped value
  - For "MATCH" verdict: raises ValueError if counterexample or offending_statements is a non-empty string; otherwise returns a tuple (False, None, None, data) where data is the parsed dict with verdict uppercased, counterexample set to None, offending_statements set to None, and reason set to its stripped value

---

### Actual Behavior

The function either raises a ValueError or returns a tuple. In case of a ValueError, one of the following conditions holds: (1) response is not valid JSON (ValueError with message starting 'spec-check response is not valid JSON:'); (2) the parsed JSON is not a dict (ValueError: 'spec-check JSON must be an object'); (3) the dict lacks any of the required fields 'verdict', 'counterexample', 'offending_statements', 'reason' (ValueError: 'spec-check JSON missing required field(s): ...'); (4) the 'verdict' field, after uppercasing if string, is not 'MATCH' or 'MISMATCH' (ValueError: 'spec-check JSON verdict must be MATCH or MISMATCH'); (5) 'counterexample' is neither None nor a string ('spec-check JSON field counterexample must be a string or null'); (6) 'offending_statements' is neither None nor a string ('spec-check JSON field offending_statements must be a string or null'); (7) 'reason' is not a string ('spec-check JSON field reason must be a string'); (8) verdict is 'MISMATCH' and any of 'counterexample', 'offending_statements', 'reason' is missing or is not a non-empty string after stripping (ValueError: 'spec-check MISMATCH JSON missing non-empty field(s): ...'); (9) verdict is 'MATCH' and either 'counterexample' or 'offending_statements' is a non-empty string after stripping (ValueError: 'spec-check MATCH JSON must not include counterexample or offending_statements'). If the function returns normally, it returns a tuple (is_mismatch, offending_stmt, reason_str, data_dict) where: is_mismatch is a boolean (True if verdict is 'MISMATCH', else False); offending_stmt is a non-empty stripped string when is_mismatch is True, otherwise None; reason_str is a stripped string (non-empty when is_mismatch is True, may be empty otherwise); data_dict is the parsed dict updated with 'verdict' set to the normalized uppercase verdict, 'counterexample' and 'offending_statements' set to stripped strings (MISMATCH) or None (MATCH), and 'reason' set to the stripped value.

---

## Code Evidence

Line 27: def _nonempty_string(value):
Line 28:     return isinstance(value, str) and bool(value.strip())
Line 47:     if _nonempty_string(counterexample) or _nonempty_string(offending_statements):

---

## Trigger Condition

The specification requires raising a ValueError if counterexample or offending_statements is a non-empty string for a MATCH verdict, but the code treats whitespace-only strings as empty and does not raise an error, violating the requirement.

---

## How to trigger the bug

The function `_parse_spec_check_json` in `src/prompts.py` uses a helper `_nonempty_string()` to check whether `counterexample` or `offending_statements` is a non-empty string for MATCH verdicts. However, `_nonempty_string()` calls `bool(value.strip())`, which strips leading and trailing whitespace before checking emptiness. This means whitespace-only strings like `"   "` are treated as empty, and the function does not raise `ValueError` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| `response` (JSON string) | `{"verdict": "MATCH", "counterexample": "   ", "offending_statements": null, "reason": "all good"}` |

### Expected (spec-correct) Output

`ValueError` raised because `counterexample` is a non-empty string.

### Actual (buggy) Output

`(False, None, None, {'verdict': 'MATCH', 'counterexample': None, 'offending_statements': None, 'reason': 'all good'})` — a tuple is returned without error.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import json
from src.prompts import _parse_spec_check_json

input_json = json.dumps({
    "verdict": "MATCH",
    "counterexample": "   ",
    "offending_statements": None,
    "reason": "all good"
})

result = _parse_spec_check_json(input_json)
print(result)
# actual (buggy) output: (False, None, None, {'verdict': 'MATCH', 'counterexample': None, 'offending_statements': None, 'reason': 'all good'})
# expected (correct) output: ValueError raised
```

---

## Probe Script

```py
import sys
import os
import json

# Ensure repo root is on sys.path so 'import src' works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.prompts import _parse_spec_check_json

    # The spec says for MATCH verdict, any non-empty string in counterexample
    # or offending_statements should raise ValueError.
    # The code uses _nonempty_string() which strips whitespace first,
    # so whitespace-only strings like "   " are treated as empty.
    # This test passes a whitespace-only counterexample to trigger the bug.

    input_json = json.dumps({
        "verdict": "MATCH",
        "counterexample": "   ",
        "offending_statements": None,
        "reason": "all good"
    })

    actual = None
    expected = "ValueError"

    result = _parse_spec_check_json(input_json)
    # No ValueError raised → BUG CONFIRMED (spec violated)
    actual = "no error (returned tuple: %s)" % str(result)

    # Bug: spec says should raise ValueError, but code doesn't
    passed = True  # True means bug reproduced (actual != expected)
except ValueError as e:
    # ValueError raised → spec-correct behavior, bug NOT reproduced
    actual = "ValueError('%s')" % str(e)
    passed = False
except Exception as e:
    print('ERROR:', str(e))
    sys.exit(1)

if passed:
    print('CONFIRMED — actual: %s | expected: %s' % (actual, expected))
else:
    print('NOT CONFIRMED — actual matched expected: %s' % actual)
```

### Probe Output

```
CONFIRMED — actual: no error (returned tuple: (False, None, None, {'verdict': 'MATCH', 'counterexample': None, 'offending_statements': None, 'reason': 'all good'})) | expected: ValueError
```
