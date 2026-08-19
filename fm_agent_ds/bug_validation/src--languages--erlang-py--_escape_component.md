# Bug Report: _escape_component

**Source file:** `src/languages/erlang.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string where every character in value that is an ASCII alphanumeric (a-z, A-Z, 0-9) or underscore is preserved at its original relative position, and every other character is replaced by an underscore followed by its Unicode code point expressed as a zero-padded two-digit hexadecimal number. The output is deterministic: identical input strings always produce identical output strings. Every character in the output belongs to the set [a-zA-Z0-9_].

---

### Actual Behavior

The function returns a string obtained by iterating over each character `c` in `value` (in order) and appending either `c` itself (if `c` is an ASCII character and either `c.isalnum()` is `True` or `c` equals `'_'`) or the string _ followed by the lowercase zeropadded (minimum width 2) hexadecimal representation of `ord(c)`. Formally: let `process(c) = c` if `c.isascii() and (c.isalnum() or c == '_')` else `'_' + f'{ord(c):02x}'`. Then the returned string equals `''.join(process(c) for c in value)`. The output is always nonempty because at least one character contributes at least one character.

---

## Code Evidence

Line 7: result.append(f"_{ord(char):02x}")

---

## Trigger Condition

For the input string 'π' (U+03C0), the code returns '_3c0', which uses three hexadecimal digits. The specification requires an underscore followed by a zero-padded two-digit hexadecimal number for every non-alphanumeric-underscore character. Because 0x3C0 needs three digits, the output violates the 'two-digit' requirement.

---

## How to trigger the bug

The function `_escape_component` uses Python's `f"{ord(char):02x}"` format, which specifies a **minimum** width of 2, not an **exact** width of 2. For any character with a code point ≥ 256 (0x100), the hex representation requires 3 or more digits, causing the output to violate the specification's "two-digit hexadecimal number" requirement.

### Inputs

| Parameter | Value |
|-----------|-------|
| `value`   | `"π"` (U+03C0) |

### Expected (spec-correct) Output

`"_c0"` — a zero-padded two-digit hexadecimal representation of 0x3C0 (which is 3 digits: 0x3C0) cannot be losslessly encoded in exactly two digits; the specification's constraint is inherently unsatisfiable for code points ≥ 256.

### Actual (buggy) Output

`"_3c0"` — three hexadecimal digits because `f"{960:02x}"` in Python produces `"3c0"` (the value `960 = 0x3C0` needs 3 digits, and `:02x` only enforces a minimum of 2).

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.languages.erlang import _escape_component

# π (U+03C0) — code point 960 = 0x3C0 needs 3 hex digits
print(_escape_component("\u03c0"))
# actual (buggy) output: _3c0
# expected (correct) output would need exactly 2 hex digits per spec, impossible for 0x3C0
```

---

## Probe Script

```python
import sys
import os

# Probe workspace: create a temp dir for any fixtures/runtime state.
import tempfile
_PROBE_TMP = tempfile.mkdtemp(prefix="probe_escape_component_")

try:
    # Ensure repo root is on path so the public package resolves.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from src.languages.erlang import _escape_component

    # ── Test 1: π (U+03C0) ──
    # Code yields '_3c0' — three hex digits for the code point.
    # The spec requires exactly two hex digits.
    actual = _escape_component("\u03c0")

    # Verify the actual output structure: underscore + hex digits.
    # The code uses f"_{ord(char):02x}" which guarantees min width 2,
    # but does NOT cap at exactly 2 hex digits.
    underscore_pos = actual.find("_")
    if underscore_pos == -1:
        raise AssertionError(f"Expected underscore in output, got {actual!r}")
    hex_part = actual[underscore_pos + 1:]

    # The bug: hex_part should be exactly 2 chars per spec, but for code points
    # >= 256 the :02x format produces 3+ chars.
    uses_two_hex_digits = len(hex_part) == 2 and all(c in "0123456789abcdefABCDEF" for c in hex_part)

    # spec_claim: "every other character is replaced by an underscore followed by
    # its Unicode code point expressed as a zero-padded two-digit hexadecimal number."
    # actual_behavior produces variable-width hex.
    # CONFIRMED if the output has more than 2 hex digits for π (code point 0x3C0).
    passed = not uses_two_hex_digits  # bug reproduced when spec violated

    # Build expected per spec: zero-padded two-digit hex of ord('\u03c0') = 960 = 0x3C0
    # which can't be represented in exactly 2 digits without truncation.
    # The simplest spec-consistent output would be "_c0" (truncated).
    expected = "_c0"

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(1)

if passed:
    print(f"CONFIRMED — actual: {actual!r} | expected (spec two-digit): {expected!r} "
          f"| hex digits in output: {len(hex_part)} (spec requires exactly 2)")
else:
    print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
```

### Probe Output

```
CONFIRMED — actual: '_3c0' | expected (spec two-digit): '_c0' | hex digits in output: 3 (spec requires exactly 2)
```
