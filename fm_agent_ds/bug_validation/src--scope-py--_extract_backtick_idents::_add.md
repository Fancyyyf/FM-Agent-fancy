# Bug Report: _add

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/src/scope.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

If the lowercased form of token with all leading underscores removed has length at least 2, is not a Python reserved keyword, and is not a member of the stop-word set, then that cleaned form is inserted into the enclosing function's mutable result collection. If any of those conditions fails, the function returns without modifying any observed state.

---

### Actual Behavior

After execution, the set `result` is updated as follows: let `t = token.lower().strip('_')`. If `len(t) >= 2` and `t  _PY_KEYWORDS` and `t  _STOP`, then `result = result_old  {t}`, otherwise `result = result_old`, where `result_old` denotes the set `result` immediately before the call.

---

## Code Evidence

Line 2: t = token.lower().strip('_')

---

## Trigger Condition

The code uses strip('_') which removes trailing underscores. The specification requires removing only leading underscores, so for token 'foo_', the code inserts 'foo' instead of the required 'foo_'.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| issue_text | `` `foo_` `` |

### Expected (spec-correct) Output

`{'foo_'}`

### Actual (buggy) Output

`{'foo'}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.scope import _extract_backtick_idents

result = _extract_backtick_idents('`foo_`')
print(result)
# actual (buggy) output: {'foo'}
# expected (correct) output: {'foo_'}
```

---

## Probe Script

```python
"""Probe script for bug: src--scope-py--_extract_backtick_idents::_add

Bug: _add() uses strip('_') which removes trailing underscores,
but the spec requires removing only leading underscores.
"""

import sys
import os

# Ensure the repo root is on the path so src.scope imports correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.scope import _extract_backtick_idents
except Exception as e:
    print(f'ERROR: Failed to import _extract_backtick_idents: {e}')
    sys.exit(1)

# For token 'foo_' (backtick-enclosed), the spec says only LEADING
# underscores are removed. Since 'foo_' has no leading underscores,
# the cleaned token should be 'foo_' (trailing underscore preserved).
# But strip('_') removes the trailing underscore, producing 'foo'.

test_input = '`foo_`'
actual = _extract_backtick_idents(test_input)

# Spec-correct: 'foo_' preserved (only leading underscores removed)
expected = {'foo_'}
# Buggy: 'foo' inserted (trailing underscore stripped)
# The bug is confirmed if actual != expected AND actual == {'foo'}

passed = actual != expected and actual == {'foo'}

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual: {actual!r} | expected: {expected!r}')
```

### Probe Output

```
CONFIRMED — actual: {'foo'} | expected: {'foo_'}
```
