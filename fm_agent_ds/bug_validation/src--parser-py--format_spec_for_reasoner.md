# Bug Report: format_spec_for_reasoner

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/parser-py/format_spec_for_reasoner.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string composed of four sections separated by blank lines: (1) the value of spec["signature"], (2) a line reading "Pre-condition:" followed by the value of spec["pre_condition"] on the next line, (3) a line reading "Post-condition:" followed by the value of spec["post_condition"] on the next line. The returned string always begins with the signature value and ends with the post_condition value. Every pair of adjacent sections is separated by exactly one blank line.

---

### Actual Behavior

The function returns a string composed as follows: newline-separated concatenation of the value of key "signature" from spec (or empty string if missing, though pre-condition guarantees its presence), followed by the literal "Pre-condition:\n", the value of "pre_condition", then "\n\nPost-condition:\n", and finally the value of "post_condition". Formally: return_value = spec["signature"] + "\n\nRecipients: " + "Pre-condition:\n" + spec["pre_condition"] + "\n\nPost-condition:\n" + spec["post_condition"]. The function has no side effects, does not mutate spec, and does not raise exceptions.

---

## Code Evidence

Line 4: f"{spec.get('signature', '')}\n\n"
Line 5: f"Pre-condition:\n{spec.get('pre_condition', '')}\n\n"

---

## Trigger Condition

When spec values end with a newline, the fixed '\n\n' separators produce two blank lines between sections instead of exactly one as required by the specification.

---

## How to trigger the bug

When `spec['signature']`, `spec['pre_condition']`, or `spec['post_condition']` values end with a trailing newline character (`\n`), the literal `\n\n` separators in the f-strings concatenate with the trailing newline from the value, producing `\n\n\n` (three newlines) — which renders as two blank lines between sections instead of the single blank line required by the specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `spec['signature']` | `'def foo(x: int) -> int:\n'` |
| `spec['pre_condition']` | `'x > 0\n'` |
| `spec['post_condition']` | `'Returns x + 1\n'` |

### Expected (spec-correct) Output

`'def foo(x: int) -> int:\n\nPre-condition:\nx > 0\n\nPost-condition:\nReturns x + 1\n'`

### Actual (buggy) Output

`'def foo(x: int) -> int:\n\n\nPre-condition:\nx > 0\n\n\nPost-condition:\nReturns x + 1\n'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.parser import format_spec_for_reasoner

spec = {
    'signature': 'def foo(x: int) -> int:\n',
    'pre_condition': 'x > 0\n',
    'post_condition': 'Returns x + 1\n'
}

result = format_spec_for_reasoner(spec)

# Actual (buggy) output — extra \n between sections:
# 'def foo(x: int) -> int:\n\n\nPre-condition:\nx > 0\n\n\nPost-condition:\nReturns x + 1\n'

# Expected (correct) output — exactly one blank line between sections:
# 'def foo(x: int) -> int:\n\nPre-condition:\nx > 0\n\nPost-condition:\nReturns x + 1\n'
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path for package import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.parser import format_spec_for_reasoner
except Exception as e:
    print(f"ERROR: Could not import src.parser: {e}")
    sys.exit(1)

try:
    # Trigger condition: spec values ending with newline
    spec = {
        'signature': 'def foo(x: int) -> int:\n',
        'pre_condition': 'x > 0\n',
        'post_condition': 'Returns x + 1\n'
    }

    actual = format_spec_for_reasoner(spec)

    # Spec-correct: exactly one blank line between adjacent sections
    expected = (
        "def foo(x: int) -> int:\n"
        "\n"
        "Pre-condition:\n"
        "x > 0\n"
        "\n"
        "Post-condition:\n"
        "Returns x + 1\n"
    )

    # Bug confirmed if actual (double blank lines) differs from expected (single blank line)
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'def foo(x: int) -> int:\n\n\nPre-condition:\nx > 0\n\n\nPost-condition:\nReturns x + 1\n' | expected: 'def foo(x: int) -> int:\n\nPre-condition:\nx > 0\n\nPost-condition:\nReturns x + 1\n'
```
