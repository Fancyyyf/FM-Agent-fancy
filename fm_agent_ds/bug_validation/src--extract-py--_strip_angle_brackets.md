# Bug Report: _strip_angle_brackets

**Source file:** `fm_agent/extracted_functions/src/extract-py/_strip_angle_brackets.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a string formed from text by removing every outermost balanced '<...>' region: both the delimiting '<' and '>' characters and all content between them are stripped. Nesting is resolved  a '<' encountered inside an active '<...>' region belongs to the inner region and does not terminate the outer. Characters that are not part of any balanced '<...>' region are preserved in their original relative order. A '>' character that does not close any active '<...>' region is omitted from the result.

---

### Actual Behavior

The function returns a new string that omits all occurrences of '<' and '>', and also omits every character that appears inside a balanced pair of angle brackets (following standard nesting). Formally, define the pre-character depth d(i) for index i (0  i  len(text)) as d(0)=0, and for i0: d(i+1) = d(i)+1 if text[i]='<'; d(i+1) = max(0, d(i)-1) if text[i]='>'; d(i+1) = d(i) otherwise. Then the output string is the concatenation of all characters text[i] such that text[i]  {'<','>'} and d(i)=0. Unmatched '<' cause all subsequent characters up to the end of the string (or until a matching '>') to be treated as inside a region and thus removed; any unmatched '>' when depth is zero are also removed.

---

## Code Evidence

Line 6: if ch == '<':
Line 7: depth += 1

---

## Trigger Condition

The code unconditionally removes '<' characters, even when they are unmatched and not part of any balanced region. The specification (Condition B) requires preservation of unmatched '<', as only balanced outermost '<...>' regions (and unmatched '>') should be removed. For the input '<', the code returns '' but the specification requires '<'.

---

## How to trigger the bug

The function unconditionally increments `depth` when encountering `'<'` and never appends the character to the result. For an unmatched `'<'` with no closing `'>'`, the character is silently dropped — the depth becomes non-zero and the loop ends without ever appending it.

### Inputs

| Parameter | Value |
|-----------|-------|
| text | `'<'` |

### Expected (spec-correct) Output

`<`

### Actual (buggy) Output

`` (empty string)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.extract import _strip_angle_brackets
# actual (buggy) output: ''
# expected (correct) output: '<'
print(repr(_strip_angle_brackets('<')))
```

---

## Probe Script

```python
"""Probe script for _strip_angle_brackets bug: prevents unmatched '<' from being preserved."""
import sys

sys.path.insert(0, '.')

try:
    from src.extract import _strip_angle_brackets

    # Test case: unmatched '<' should be preserved per spec (Condition B)
    # Bug claim: the code drops '<' unconditionally, returning '' instead of '<'
    actual = _strip_angle_brackets('<')
    expected = '<'  # Spec: unmatched '<' is not part of any balanced region, preserve it
    passed = actual != expected  # True → bug reproduced (actual != expected)

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: '' | expected: '<'
```
