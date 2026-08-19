# Bug Report: _optional_string

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_optional_string.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When value is None, returns an empty string. When value is not None and not of type str, raises ValueError whose message contains source and key. When value is a string, returns a string with leading and trailing whitespace removed, trailing semicolons stripped, and surrounding matching single or double quotation marks removed; returns an empty string when the cleaned content is empty.

---

### Actual Behavior

The function either returns a string or raises a ValueError. If `value` is `None`, the function returns the empty string `""` without raising an exception. If `value` is not `None` and its type is not `str`, a `ValueError` is raised with the message `f"{source}: '{key}' must be a string"` (where `source` and `key` are the original nonempty arguments). If `value` is a `str` (non`None`), no exception is raised and the function returns the result of `_clean_label(value)`: a string obtained by stripping leading and trailing whitespace, removing all trailing semicolons, and stripping a surrounding pair of matching single or double quotation marks. If after these transformations the string is empty, the return value is the empty string. Formally: Let `clean(s)` be the described cleaning operation (which may return `""`). Then (value = None → R = "" ∧ ¬E) ∧ (value ≠ None ∧ ¬isinstance(value, str) → E = ValueError(msg = source + ": '" + key + "' must be a string")) ∧ (value ≠ None ∧ isinstance(value, str) → ¬E ∧ R = clean(value)).

---

## Code Evidence

Line 4: if not isinstance(value, str):

---

## Trigger Condition

When value is an instance of a subclass of str, the code treats it as a valid string (isinstance check passes) and returns the cleaned string. However, the specification states that if value is not of type str (i.e., type(value) is not exactly str), a ValueError should be raised. Thus, for any value that is a subclass of str, the code violates the specification by not raising ValueError.

---

## How to trigger the bug

The code uses `isinstance(value, str)` on line 185 of `src/call_graph_edges.py` (line 4 of the extracted function), which allows any subclass of `str` to pass the type check. The specification requires an exact `type()` check — only instances whose type is exactly `str` (not a subclass) should be accepted. Passing a `str` subclass instance silently returns the cleaned string instead of raising `ValueError` as the spec demands.

### Inputs

| Parameter | Value |
|-----------|-------|
| `value` | `MyString("hello")` where `MyString` is a subclass of `str` |
| `key` | `"test_key"` |
| `source` | `"test_source"` |

### Expected (spec-correct) Output

`ValueError` with message `"test_source: 'test_key' must be a string"`

### Actual (buggy) Output

`"hello"` (the cleaned string, because `isinstance()` returned `True` for the subclass)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.call_graph_edges import _optional_string

class MyString(str):
    pass

value = MyString("hello")
# The spec requires ValueError here because type(value) is not str,
# but isinstance(value, str) is True, so the code returns 'hello' instead.
result = _optional_string(value, "test_key", "test_source")
# actual (buggy) output: "hello"
# expected (correct) output: ValueError("test_source: 'test_key' must be a string")
```

---

## Probe Script

```python
"""Probe script for _optional_string bug: isinstance vs type check for str subclasses."""

import sys
import os

# Allow importing from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.call_graph_edges import _optional_string

    class MyString(str):
        """A trivial subclass of str used to test the isinstance vs type check."""
        pass

    # A str subclass instance should trigger ValueError per spec ("not of type str"),
    # but the code uses isinstance() which accepts subclasses.
    value = MyString("hello")

    try:
        result = _optional_string(value, "test_key", "test_source")
        # If we get here, no ValueError was raised — the bug is confirmed.
        # Spec says it should raise ValueError for non-exact-str types.
        expected_error_msg = "test_source: 'test_key' must be a string"
        print(
            "CONFIRMED — isinstance() accepted str subclass, "
            f"but spec requires exact type() check. "
            f"Returned: {result!r}"
        )
    except ValueError:
        # If ValueError IS raised, the code matches the spec — bug not confirmed.
        print(
            "NOT CONFIRMED — ValueError raised for str subclass, "
            "which matches the spec requirement"
        )
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — isinstance() accepted str subclass, but spec requires exact type() check. Returned: 'hello'
```
