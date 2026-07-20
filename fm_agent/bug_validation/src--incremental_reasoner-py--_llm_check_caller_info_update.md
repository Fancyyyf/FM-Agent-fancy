# Bug Report: _llm_check_caller_info_update

**Source file:** `src/incremental_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Constructs an LLM prompt that asks to evaluate whether the caller's [INFO]
    entry for callee_name is consistent with callee_new_spec; consistency means
    no contradictory pre-condition or post-condition exists between the
    callee's specification and the caller's recorded expectation for that
    callee
  - Sends the prompt to an LLM and validates the response against a JSON
    schema requiring keys "info_updated" (bool) and "new_info" (string)
  - When the LLM returns valid, parseable JSON, info_updated is True if and
    only if the entry for callee_name required modification to achieve
    consistency; when info_updated is True, new_info contains the complete
    replacement [INFO] block (markers included, all prior callee entries
    preserved, callee_name entry adjusted for consistency, all other entries
    byte-for-byte unchanged); when info_updated is False, new_info is the
    empty string
  - Returns None when the LLM produces no response, or when the response
    cannot be parsed as valid JSON matching the required schema
  - Domain knowledge files from under work_dir, if any exist at the expected
    location, are included in the prompt as additional context
  - The function performs no file writes and does not modify caller_source

---

### Actual Behavior

If the function terminates normally, it returns the result of `_llm_select_json`, which is either a dict `{'info_updated': bool, 'new_info': str}` satisfying `_validate_caller_info_update` or `None`. All input arguments remain unchanged. If `_llm_select_json` raises an exception, that exception propagates; no return value is produced.

---

## Code Evidence

Line 45: return _llm_select_json(
Line 49: validator=_validate_caller_info_update,

---

## Trigger Condition

The code delegates all output validation to _validate_caller_info_update. If this validator only enforces JSON types and not the semantic constraints on new_info (complete replacement block, byte-for-byte preservation of other entries, etc.), a valid JSON response like {'info_updated': True, 'new_info': 'arbitrary garbage'} will be returned by the function. This violates the specification which requires that when info_updated is True, new_info must contain the complete replacement [INFO] block with markers, all prior entries preserved, and only the callee_name entry adjusted.

---

## How to trigger the bug

The bug is triggered whenever the LLM returns a response that is well-typed JSON (correct `info_updated` and `new_info` fields with correct types) but whose `new_info` value does not meet the semantic requirements of being a complete replacement `[INFO]` block. The `_validate_caller_info_update` validator only checks types and non-emptiness, so arbitrary string content passes through.

### Inputs

| Parameter | Value |
|-----------|-------|
| `data` | `{"info_updated": true, "new_info": "arbitrary garbage, not a valid [INFO] block"}` |

### Expected (spec-correct) Output

`ValueError` raised — `new_info` must contain a complete `[INFO]` block with markers, all prior callee entries preserved byte-for-byte, only the callee_name entry adjusted.

### Actual (buggy) Output

`{'info_updated': True, 'new_info': 'arbitrary garbage, not a valid [INFO] block'}` (returned without error)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, ".")
from src.incremental_reasoner import _validate_caller_info_update

data = {"info_updated": True, "new_info": "arbitrary garbage, not a valid [INFO] block"}
result = _validate_caller_info_update(data)
# actual (buggy) output: {'info_updated': True, 'new_info': 'arbitrary garbage, not a valid [INFO] block'}
# expected (correct) output: ValueError raised
```

---

## Probe Script

```python
import sys
import os

# Add the project root to sys.path so 'config' and 'src' package are importable.
_snapshot_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _snapshot_root)

try:
    # Import via the public 'src' package entry point.
    from src.incremental_reasoner import _validate_caller_info_update

    data = {"info_updated": True, "new_info": "arbitrary garbage, not a valid [INFO] block"}

    result = _validate_caller_info_update(data)

    expected = "ValueError raised — new_info must be a complete [INFO] block"
    actual = result
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")

except ValueError:
    print("NOT CONFIRMED — validator correctly rejected invalid new_info content")
except ImportError:
    # Module-level imports (config, openai, etc.) may fail in this environment.
    # Fall back to testing the validator logic in isolation (verbatim copy from source).

    def _validate_caller_info_update(data):
        """Validate a direct LLM decision about one caller's [INFO] block."""
        if not isinstance(data, dict):
            raise ValueError("caller-info JSON must be an object")
        required = ("info_updated", "new_info")
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError("caller-info JSON missing required field(s): " + ", ".join(missing))
        if not isinstance(data["info_updated"], bool):
            raise ValueError("caller-info JSON field info_updated must be a boolean")
        if not isinstance(data["new_info"], str):
            raise ValueError("caller-info JSON field new_info must be a string")
        if data["info_updated"] and not data["new_info"].strip():
            raise ValueError("caller-info JSON requires non-empty new_info when info_updated is true")
        return {"info_updated": data["info_updated"], "new_info": data["new_info"].strip()}

    data = {"info_updated": True, "new_info": "arbitrary garbage, not a valid [INFO] block"}
    try:
        result = _validate_caller_info_update(data)
        expected = "ValueError raised — new_info must be a complete [INFO] block"
        print(f"CONFIRMED — actual: {result!r} | expected: {expected!r}")
    except ValueError:
        print("NOT CONFIRMED — validator correctly rejected invalid new_info content")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: {'info_updated': True, 'new_info': 'arbitrary garbage, not a valid [INFO] block'} | expected: 'ValueError raised — new_info must be a complete [INFO] block'
```
