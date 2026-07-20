# Bug Report: _escape_component

**Source file:** `src/languages/erlang-py/_escape_component.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an escaped representation of value suitable for use as a component in a fully-qualified name (FQN) where double-underscore ("__") serves as the component separator
  - The returned string contains no occurrence of the substring "__"
  - When value is non-empty, the returned string is non-empty
  - Each character of value that is an ASCII alphanumeric or underscore is preserved as-is at its original position
  - Every other character is replaced by an underscore followed by the lowercase hexadecimal representation of its Unicode code point (zero-padded to at least 2 digits), preserving the original relative order of all characters

---

### Actual Behavior

The returned string is the concatenation, in order, of the transformation of each character c in the input string value: if c is an ASCII alphanumeric character (as determined by c.isascii() and c.isalnum()) or the underscore '_', then c itself; otherwise the string consisting of an underscore followed by the two-digit hexadecimal representation of ord(c) (using lowercase letters). Formally: result == ''.join(c if (c.isascii() and (c.isalnum() or c == '_')) else f'_{ord(c):02x}' for c in value).

---

## Code Evidence

Line 4-7: the loop does not check for or avoid producing double underscore

---

## Trigger Condition

For input '_:' the code converts '_' to '_' and ':' to '_3a', resulting in '__3a' which contains the substring '__', violating the specification requirement that the returned string contains no occurrence of '__'.

---

## How to trigger the bug

The bug occurs when the input string contains an underscore character followed by any non-alphanumeric character that gets escaped to a `_xx` pattern. The underscore is preserved as-is, and the next character's hex escape begins with an underscore, producing a forbidden `__` sequence.

### Inputs

| Parameter | Value |
|-----------|-------|
| value | `_:` |

### Expected (spec-correct) Output

A string containing no occurrence of `__`. For example, `_5f_3a` (if underscores were also escaped) or any other encoding that avoids `__`.

### Actual (buggy) Output

`__3a`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
from src.languages.erlang import _escape_component

actual = _escape_component("_:")
print(actual)
# actual (buggy) output: __3a
# expected (correct) output: any string without "__"
```

---

## Probe Script

```python
"""Probe script for bug src--languages--erlang-py--_escape_component.

The bug: _escape_component does not prevent double-underscore ("__") in output
when an underscore in the input is followed by a character that escapes to '_xx'.

Trigger condition: input "_:" yields "__3a" which violates the spec.
"""
import sys

try:
    from src.languages.erlang import _escape_component
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

input_value = "_:"
try:
    actual = _escape_component(input_value)
except Exception as e:
    print(f'ERROR: call failed — {e}')
    sys.exit(1)

# The spec requires: "The returned string contains no occurrence of the substring '__'"
# The buggy code produces '__3a' which violates this.
has_double_underscore = "__" in actual
passed = has_double_underscore  # True → bug confirmed

if passed:
    print(f'CONFIRMED — input {input_value!r} produced {actual!r} which contains "__"')
else:
    print(f'NOT CONFIRMED — input {input_value!r} produced {actual!r} without "__"')
```

### Probe Output

```
CONFIRMED — input '_:' produced '__3a' which contains "__"
```
