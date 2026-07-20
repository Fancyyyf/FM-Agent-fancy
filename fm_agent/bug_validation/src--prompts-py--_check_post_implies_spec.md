# Bug Report: _check_post_implies_spec

**Source file:** `src/prompts-py/_check_post_implies_spec.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a tuple (passed: bool, offending_stmts: str|None, computed_post_cond: str|None, violation_reason: str|None)
  - When the set of program states described by post_condition is a subset of the set described by spec_post_condition (i.e., post_condition logically implies spec_post_condition for all valid inputs), returns (True, None, None, None)
  - When there exists a concrete valid input for which post_condition does not guarantee spec_post_condition, returns (False, offending_stmts, post_condition, violation_reason) where offending_stmts and violation_reason are non-empty strings
  - offending_stmts preserves "Line N:" prefixes from block when present, identifying the specific statements responsible for the violation
  - When no definitive MATCH or MISMATCH verdict can be reached after exhausting retry attempts, raises ValueError

---

### Actual Behavior

If _retry_create raises an exception E, then response remains None, usage remains {}, an event with status 'error' is recorded, and the exception E is reraised. If _retry_create succeeds, returning (resp, usg), then response = resp and usage = usg. In that case, if _parse_spec_check_json(resp) raises a ValueError exc_parse, then has_violation = None, stmts = None, reason = None, parse_error = str(exc_parse), status = 'format_error', messages is extended with an assistant message containing resp and a user message requesting valid JSON, and a new ValueError with message 'Could not parse a valid structured JSON verdict from spec-check response.' is raised. If _parse_spec_check_json(resp) succeeds, returning (hv, stm, rsn, prs), then parsed_result = prs, parse_error = None, and status = 'mismatch' if hv else 'success'. After recording an event, if hv is False, the function returns (True, None, None, None). If hv is True, stmts is replaced by stm if stm is truthy else '(unable to extract)', reason is replaced by rsn if rsn is truthy else '(unable to extract)', and the function returns (False, stmts, post_condition, reason). In all nonexception paths that reach a return, messages remains as it was before the code block. All variables from the precondition not explicitly modified (attempt, info_str, lang_expertise, trace_meta, event_id, started, language, block, spec_post_condition, etc.) retain their original values. Formally: ( E : _retry_create raised E  response = None  usage = {}   return  raised(E))  ( resp, usg : _retry_create returned (resp, usg)  response = resp  usage = usg  ( ( exc_parse : _parse_spec_check_json(resp) raised ValueError exc_parse  has_violation = None  stmts = None  reason = None  parse_error = str(exc_parse)  status = 'format_error'  messages = old_messages + [{'role':'assistant','content':resp or ''}, {'role':'user','content':'Return only valid JSON...'}]  raised(ValueError('Could not parse a valid structured JSON verdict from spec-check response.')))  ( prs : _parse_spec_check_json(resp) returned (hv, stm, rsn, prs)  parsed_result = prs  parse_error = None  status = 'mismatch' if hv else 'success'  event recorded  ( hv = False  return (True, None, None, None) )  ( hv = True  stmts = stm if stm else '(unable to extract)'  reason = rsn if rsn else '(unable to extract)'  return (False, stmts, post_condition, reason) ) ) ) )

---

## Code Evidence

Line 62: raise

---

## Trigger Condition

The specification requires raising ValueError when no definitive MATCH or MISMATCH verdict can be reached after exhausting retry attempts. The code re-raises the original exception from _retry_create, which may be something other than ValueError, violating the specification.

---

## How to trigger the bug

When the underlying LLM call (`_retry_create`) raises a non-ValueError exception (e.g., a network error like `RuntimeError`, `ConnectionError`, or `urllib.error.HTTPError`), the `except Exception` handler in `_check_post_implies_spec` catches it, records a trace event, and then executes a bare `raise` statement. This re-raises the original exception type rather than wrapping it in or converting it to a `ValueError`. The specification requires that any failure to reach a definitive verdict after exhausting retries raises `ValueError` — but a bare `raise` preserves the original exception type, violating the spec.

### Inputs

| Parameter | Value |
|-----------|-------|
| `func` | `def double(x):\n    return x * 2\n` |
| `spec` | `Pre-condition:\n  x is a valid integer\nPost-condition:\n  returns x * 2` |
| `info` | `""` |
| `language` | `"python"` |
| `_retry_create` (patched) | `side_effect=RuntimeError("simulated _retry_create failure")` |

### Expected (spec-correct) Output

`ValueError` should be raised (per specification: "When no definitive MATCH or MISMATCH verdict can be reached after exhausting retry attempts, raises ValueError")

### Actual (buggy) Output

`RuntimeError` is raised (the bare `raise` on line 88 of `src/prompts.py` re-raises the original `_retry_create` exception without converting to `ValueError`)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
repo_root = "."
sys.path.insert(0, repo_root)

from unittest.mock import patch
from src.reasoner import reasoner

spec_text = (
    "Pre-condition:\n"
    "  x is a valid integer\n"
    "Post-condition:\n"
    "  returns x * 2\n"
)
func_text = "def double(x):\n    return x * 2\n"

with patch("src.prompts._retry_create", side_effect=RuntimeError("simulated _retry_create failure")):
    try:
        reasoner(func=func_text, spec=spec_text, info="", language="python")
    except ValueError:
        print("ValueError — spec satisfied")
    except RuntimeError as e:
        print(f"BUG: got RuntimeError instead of ValueError: {e}")
// actual (buggy) output: RuntimeError: simulated _retry_create failure
// expected (correct) output: ValueError
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on the path so that 'src' and 'config' imports work
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

from unittest.mock import patch

try:
    # Import the public API function that exercises the buggy code path
    from src.reasoner import reasoner

    # The spec says: when no definitive MATCH/MISMATCH verdict can be reached after
    # exhausting retry attempts, raises ValueError.
    # The bug: if _retry_create raises a non-ValueError exception (e.g., network error),
    # the bare `raise` on line 88 of prompts.py re-raises it as-is instead of ValueError.
    #
    # Trigger: monkey-patch _retry_create to raise RuntimeError, then call reasoner().
    # If bug exists, RuntimeError will propagate (CONFIRMED).
    # If bug is fixed, ValueError should be raised (NOT CONFIRMED).

    spec_text = (
        "Pre-condition:\n"
        "  x is a valid integer\n"
        "Post-condition:\n"
        "  returns x * 2\n"
    )
    func_text = "def double(x):\n    return x * 2\n"

    got_value_error = False
    got_other_exception = None

    with patch("src.prompts._retry_create", side_effect=RuntimeError("simulated _retry_create failure")):
        try:
            reasoner(
                func=func_text,
                spec=spec_text,
                info="",
                language="python",
            )
        except ValueError:
            got_value_error = True
        except Exception as e:
            got_other_exception = (type(e).__name__, str(e))

    if got_other_exception is not None:
        print(
            f"CONFIRMED — spec requires ValueError but got {got_other_exception[0]}: "
            f"{got_other_exception[1]}"
        )
    elif got_value_error:
        print("NOT CONFIRMED — got expected ValueError as spec requires")
    else:
        print("NOT CONFIRMED — no exception raised at all")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — spec requires ValueError but got RuntimeError: simulated _retry_create failure
```
