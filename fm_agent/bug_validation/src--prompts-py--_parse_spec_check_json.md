# Bug Report: _parse_spec_check_json

**Source file:** `src/prompts-py/_parse_spec_check_json.py`
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

Given a non-empty string `response`, the function `_parse_spec_check_json` either raises a `ValueError` or returns a tuple `(match_flag, offending, reason, data)`. The possible outcomes are:

1. If `_load_spec_check_json(response)` raises a `JSONDecodeError`, a `ValueError` with message `spec-check response is not valid JSON: {exc}` is raised.
2. Otherwise, let `data` be the parsed JSON object. If `data` is not a dictionary (`not isinstance(data, dict)`), a `ValueError` with message `spec-check JSON must be an object` is raised.
3. If any of the required fields `'verdict'`, `'counterexample'`, `'offending_statements'`, `'reason'` are missing from `data`, a `ValueError` is raised with message `spec-check JSON missing required field(s): ...` listing the missing keys.
4. Otherwise, let `verdict_raw = data['verdict']`, `counterexample_raw = data.get('counterexample')`, `offending_statements_raw = data.get('offending_statements')`, `reason_raw = data.get('reason')`. Let `verdict = verdict_raw.upper() if isinstance(verdict_raw, str) else verdict_raw`. If `verdict not in ('MATCH', 'MISMATCH')`, a `ValueError` is raised with message `spec-check JSON verdict must be MATCH or MISMATCH`.
5. If `counterexample_raw is not None and not isinstance(counterexample_raw, str)`, raise `ValueError('spec-check JSON field counterexample must be a string or null')`. If `offending_statements_raw is not None and not isinstance(offending_statements_raw, str)`, raise `ValueError('spec-check JSON field offending_statements must be a string or null')`. If `not isinstance(reason_raw, str)`, raise `ValueError('spec-check JSON field reason must be a string')`.
6. Update `data['verdict'] = verdict`.
   - **Case MISMATCH** (`verdict == 'MISMATCH'`):
       - Define `valid = lambda x: isinstance(x, str) and bool(x.strip())`. If any of `counterexample_raw`, `offending_statements_raw`, `reason_raw` fails `valid(x)`, raise `ValueError('spec-check MISMATCH JSON missing non-empty field(s): ...')` listing those failing.
       - Else, set `data['counterexample'] = counterexample_raw.strip()`, `data['offending_statements'] = offending_statements_raw.strip()`, `data['reason'] = reason_raw.strip()`. Return `(True, data['offending_statements'], data['reason'], data)`.
   - **Case MATCH** (`verdict == 'MATCH'`):
       - If `valid(counterexample_raw)` or `valid(offending_statements_raw)`, raise `ValueError('spec-check MATCH JSON must not include counterexample or offending_statements')`.
       - Else, set `data['counterexample'] = None`, `data['offending_statements'] = None`, `data['reason'] = reason_raw.strip()`. Return `(False, None, None, data)`.

Formally:
\[
\begin{aligned}
&\text{pre: } response \in \Sigma^+ \\
&\text{post: } \left( \begin{aligned}
&(\neg valid\_json(response) \Rightarrow \text{raise ValueError}) \\
&\land (valid\_json(response) \land D = parse(response) \land \neg isinstance(D, dict) \Rightarrow \text{raise ValueError}) \\
&\land (isinstance(D, dict) \land keys\_missing(D) \Rightarrow \text{raise ValueError}) \\
&\land (isinstance(D, dict) \land \neg keys\_missing(D) \land \neg valid\_verdict(D) \Rightarrow \text{raise ValueError}) \\
&\land (\text{valid fields and verdict} \land \neg valid\_counterexample\_type(D) \Rightarrow \text{raise ValueError}) \\
&\land (\text{valid fields and verdict} \land \neg valid\_offending\_type(D) \Rightarrow \text{raise ValueError}) \\
&\land (\text{valid fields and verdict} \land \neg valid\_reason\_type(D) \Rightarrow \text{raise ValueError}) \\
&\land (\text{valid types} \land verdict\_up = \text{MISMATCH} \land \neg all\_nonempty\_strings(D) \Rightarrow \text{raise ValueError listing failing fields}) \\
&\land (\text{valid types} \land verdict\_up = \text{MISMATCH} \land all\_nonempty\_strings(D) \Rightarrow \text{return } (True, strip(O), strip(R), D')) \\
&\land (\text{valid types} \land verdict\_up = \text{MATCH} \land (nonempty\_str(C) \lor nonempty\_str(O)) \Rightarrow \text{raise ValueError}) \\
&\land (\text{valid types} \land verdict\_up = \text{MATCH} \land \neg nonempty\_str(C) \land \neg nonempty\_str(O) \Rightarrow \text{return } (False, None, None, D''))
\end{aligned} \right)
\end{aligned}
\]
where predicates follow the Python code semantics.

---

## Code Evidence

Line 47: if _nonempty_string(counterexample) or _nonempty_string(offending_statements):
Line 48:     raise ValueError(
Line 49:         "spec-check MATCH JSON must not include counterexample or offending_statements"
Line 50:     )

---

## Trigger Condition

The specification states: for MATCH verdict, raises ValueError if counterexample or offending_statements is a non-empty string. A whitespace-only string (e.g., '   ') is a non-empty string (length > 0), so it should raise ValueError. The code's _nonempty_string checks bool(value.strip()), treating whitespace-only strings as empty, and does not raise an error, violating the spec.

---

## How to trigger the bug

The `_nonempty_string` helper function (line 64) uses `bool(value.strip())` to determine "non-empty". A whitespace-only string like `"   "` has length > 0 (non-empty) but `.strip()` yields `""` (falsy). The spec requires `ValueError` for any non-empty string, but the code silently accepts whitespace-only `counterexample` / `offending_statements` for MATCH verdicts and returns a tuple instead.

### Inputs

| Parameter | Value |
|---|---|
| `response` | `{"verdict": "MATCH", "counterexample": "   ", "offending_statements": "   ", "reason": "The code behaves correctly."}` |

### Expected (spec-correct) Output

`ValueError` with message: `"spec-check MATCH JSON must not include counterexample or offending_statements"`

### Actual (buggy) Output

`(False, None, None, data)` — a 4-tuple with no error, where `data` is the parsed dict with `counterexample` and `offending_statements` set to `None`.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import json
from src.prompts import _parse_spec_check_json

# MATCH verdict with whitespace-only counterexample and offending_statements
response = json.dumps({
    "verdict": "MATCH",
    "counterexample": "   ",
    "offending_statements": "   ",
    "reason": "The code behaves correctly.",
})

# Per spec, this should raise ValueError.
# Per code, it returns (False, None, None, ...) without error.
result = _parse_spec_check_json(response)
# actual (buggy) output: (False, None, None, data) — no error
# expected (correct) output: ValueError
```

---

## Probe Script

```py
"""Probe for bug: _nonempty_string treats whitespace-only strings as empty,
violating the _parse_spec_check_json spec for MATCH verdict."""

import json
import sys

# Add repo root to path so src.prompts import resolves
sys.path.insert(0, ".")

try:
    from src.prompts import _parse_spec_check_json
except ImportError as e:
    print(f"ERROR: Could not import _parse_spec_check_json: {e}")
    sys.exit(1)

# Build a MATCH-verdict JSON where counterexample is a whitespace-only string.
# Per the spec, any non-empty string (length > 0) should trigger ValueError.
# The code's _nonempty_string uses bool(value.strip()), which treats
# whitespace-only as empty and does NOT raise.
match_with_whitespace_counterexample = json.dumps({
    "verdict": "MATCH",
    "counterexample": "   ",
    "offending_statements": "   ",
    "reason": "The code behaves correctly.",
})

try:
    result = _parse_spec_check_json(match_with_whitespace_counterexample)
    # No ValueError → bug reproduced.
    actual = result
    expected = "ValueError"
    print(f"CONFIRMED — _nonempty_string treats whitespace-only as empty, "
          f"but spec requires ValueError for any non-empty string. "
          f"Actual: returned tuple {result[:3]!r} (no error) | Expected: {expected!r}")
except ValueError:
    # ValueError raised → spec-correct behavior.
    print("NOT CONFIRMED — ValueError correctly raised for whitespace-only counterexample/offending_statements")
except Exception as e:
    print(f"ERROR: Unexpected exception: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — _nonempty_string treats whitespace-only as empty, but spec requires ValueError for any non-empty string. Actual: returned tuple (False, None, None) (no error) | Expected: 'ValueError'
```
