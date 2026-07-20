# Bug Report: _extract_function_name

**Source file:** `src/parser.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns the function name extracted from the signature line; returns None if
    no recognizable function name is found
  - A function name is recognizable when signature_line contains an identifier
    (starting with an alphabetic character or underscore, followed by zero or more
    alphanumeric characters or underscores) immediately followed by optional
    whitespace and an opening parenthesis `(`
  - When multiple such patterns exist in signature_line, the first (leftmost) match
    determines the returned function name

---

### Actual Behavior

The function returns the first identifier-like substring immediately followed by an opening parenthesis in `signature_line`, or `None` if no such pattern exists. The input string `signature_line` remains unchanged. Formally: let `m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', signature_line)`. Then: if `m` is not `None`, the return value is `m.group(1)` (a string); if `m` is `None`, the return value is `None`. That is, `( m  MatchObject  {None} : m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', signature_line)  ( (m  None  return_value = m.group(1)  isinstance(return_value, str))  (m = None  return_value = None) ))`.

---

## Code Evidence

Line 2:     match = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', signature_line)

---

## Trigger Condition

The code uses a regular expression that only matches ASCII letters (A-Z, a-z) for the initial character of the identifier. The specification requires recognition of identifiers starting with any alphabetic character, which in Python includes Unicode letters. A function name like 'café' (with a non-ASCII letter é) is a valid identifier and should be extracted, but the code returns None instead of 'café'.

---

## How to trigger the bug

The regex `([A-Za-z_][A-Za-z0-9_]*)` only matches ASCII letters and digits. Python 3 identifiers may contain Unicode letters (PEP 3131). When a function signature contains a Unicode character in its name, the regex fails to match, and the function incorrectly returns `None` instead of extracting the identifier.

### Inputs

| Parameter | Value |
|-----------|-------|
| signature_line | `'café(x)'` |

### Expected (spec-correct) Output

`'café'`

### Actual (buggy) Output

`None`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src import parser
result = parser._extract_function_name('caf\xe9(x)')
# actual (buggy) output: None
# expected (correct) output: 'café'
```

---

## Probe Script

```python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../..')

try:
    from src import parser

    signature = 'caf\xe9(x)'
    actual = parser._extract_function_name(signature)
    expected = 'caf\xe9'
    passed = actual is None

    if passed:
        print(f'CONFIRMED — actual: {actual!r} (None) | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: None (None) | expected: 'café'
```
