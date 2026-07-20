# Bug Report: _load_spec_check_json

**Source file:** `src/prompts-py/_load_spec_check_json.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a dict, which is the Python object produced by deserializing the JSON content extracted from response
  - Raises json.JSONDecodeError if response does not contain extractable JSON
  - Raises json.JSONDecodeError if the extracted JSON content is not a dict (i.e., is a list, string, number, boolean, or null)

---

### Actual Behavior

If the input string `response` contains a JSON object that can be extracted by `_parse_json_response`, the function returns the corresponding dictionary. Otherwise, it raises `json.JSONDecodeError`.

Formally: Let `parse(s)` be the result of `_parse_json_response(s)`. For any non-empty string `response`,
  ( d  dict: `parse(response)` terminates successfully and returns d)    the function returns d
  
  ( `parse(response)` raises `ValueError`    `parse(response)` returns a value that is not a `dict` )    the function raises `json.JSONDecodeError`.

---

## Code Evidence

Line 10: except ValueError as exc:

---

## Trigger Condition

When response is 42 (an integer), isinstance(response, str) is False, so text is ''. _parse_json_response(42) is called, but it expects a string and may raise TypeError. The except clause only catches ValueError, so TypeError is not translated to json.JSONDecodeError. The specification requires json.JSONDecodeError for any unextractable JSON, including non-string inputs.

---

## How to trigger the bug

The logic verifier claimed that passing a non-string value (42) to `_load_spec_check_json` would cause `_parse_json_response(42)` to raise `TypeError` — an exception NOT caught by `except ValueError`, thus escaping conversion to `json.JSONDecodeError`.

**However, this is incorrect.** `_parse_json_response` (in `src/llm_client.py`, line 258) explicitly checks `if not isinstance(response, str): raise ValueError(...)`. It raises `ValueError`, NOT `TypeError`, for non-string inputs. The `except ValueError as exc:` in `_load_spec_check_json` catches this `ValueError` and re-raises it as `json.JSONDecodeError`, satisfying the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| response | 42 (integer) |

### Expected (spec-correct) Output

`json.JSONDecodeError` — any non-extractable JSON input (including non-strings) should produce this error type.

### Actual (buggy) Output

`json.JSONDecodeError('LLM response must be a JSON string: line 1 column 1 (char 0)')` — matches the specification.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.prompts import _load_spec_check_json
import json

try:
    _load_spec_check_json(42)
    print("No exception — BUG")
except json.JSONDecodeError as e:
    print("json.JSONDecodeError raised — spec satisfied")
except TypeError as e:
    print("TypeError raised — this would be the bug")
# Actual output: json.JSONDecodeError raised — spec satisfied
```

---

## Probe Script

```python
import sys
import os
import json

# Ensure repo root is on sys.path so 'import src' works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

actual = None
expected_type = "json.JSONDecodeError"
passed = False

try:
    from src.prompts import _load_spec_check_json

    # Trigger condition: when response is 42 (an integer), isinstance(response, str) is False,
    # so text is ''. _parse_json_response(42) is called, but it expects a string and
    # may raise TypeError. The except clause only catches ValueError, so TypeError
    # is not translated to json.JSONDecodeError.
    result = _load_spec_check_json(42)
    # If we get here, no exception was raised at all → bug (spec says should raise)
    actual = "no error (returned: %r)" % result
    passed = True
except json.JSONDecodeError as e:
    # spec-correct behavior — the function properly translated the error
    actual = "json.JSONDecodeError('%s')" % str(e)
    passed = False
except TypeError as e:
    # Bug confirmed! TypeError escaped instead of being converted to JSONDecodeError
    actual = "TypeError('%s')" % str(e)
    passed = True
except ValueError as e:
    # ValueError raised instead of json.JSONDecodeError → also a bug per spec
    actual = "ValueError('%s')" % str(e)
    passed = True
except Exception as e:
    print('ERROR:', type(e).__name__, str(e))
    sys.exit(1)

if passed:
    print('CONFIRMED — actual: %s | expected: %s' % (actual, expected_type))
else:
    print('NOT CONFIRMED — actual matched expected: %s' % actual)
```

### Probe Output

```
NOT CONFIRMED — actual matched expected: json.JSONDecodeError('LLM response must be a JSON string: line 1 column 1 (char 0)')
```
