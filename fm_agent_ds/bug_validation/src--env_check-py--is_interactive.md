# Bug Report: is_interactive

**Source file:** `src/env_check-py/is_interactive.py` (actual source: `src/env_check.py`, line 112)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True when the process's standard input is connected to a terminal (TTY); returns False otherwise. No side effects.

---

### Actual Behavior

If the call to sys.stdin.isatty() completes without raising an exception, the function returns True if that call returned True, and False otherwise. If sys.stdin.isatty() raises an exception, the function does not return, and that exception propagates to the caller. Formally, for any successful call: result = sys.stdin.isatty(); for any exceptional call: exception = exception_from(sys.stdin.isatty()).

---

## Code Evidence

Line 2: return sys.stdin.isatty()

---

## Trigger Condition

The specification requires the function to return `True` when stdin is connected to a terminal and `False` otherwise. It does not allow raising exceptions. The code unconditionally delegates to `sys.stdin.isatty()`, which can raise exceptions (e.g., when stdin is closed or not a proper file object). In such cases, the code fails to meet the specification by propagating the exception instead of returning `False`.

---

## How to trigger the bug

The function `is_interactive()` directly delegates to `sys.stdin.isatty()` without any exception handling. When `sys.stdin.isatty()` raises an exception — for example, because the underlying file descriptor has been closed or stdin has been replaced with a non-file object — the exception propagates uncaught to the caller. The specification requires the function to always return a boolean value (False when stdin is not a TTY, including error cases). The presence of unhandled exceptions violates this contract.

### Inputs

| Parameter | Value |
|-----------|-------|
| `sys.stdin` | A mock object whose `isatty()` method raises `OSError` (simulating a closed file descriptor) |

### Expected (spec-correct) Output

`False`

### Actual (buggy) Output

`OSError: input/output error — underlying file descriptor closed` (exception propagates to caller)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys

class BrokenStdin:
    def isatty(self):
        raise OSError("underlying file descriptor closed")

saved = sys.stdin
sys.stdin = BrokenStdin()
try:
    from src.env_check import is_interactive
    result = is_interactive()
    print(f"Returned: {result}")  # may not reach here
except Exception as e:
    print(f"Exception propagated: {type(e).__name__}: {e}")
finally:
    sys.stdin = saved

# actual (buggy) output: OSError propagated to caller
# expected (correct) output: False
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe for bug: src--env_check-py--is_interactive
Bug: is_interactive() propagates sys.stdin.isatty() exceptions instead of returning False.
According to spec, the function must always return a boolean — never raise.
"""

import sys
import os

# Ensure repo root is on the path so 'from src.env_check' resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# -- Mock stdin whose isatty() raises to simulate a closed/broken file descriptor --
class _BrokenStdin:
    """Minimal stdin-like object whose isatty() raises to mimic a closed fd."""
    def isatty(self):
        raise OSError("input/output error — underlying file descriptor closed")

_original_stdin = sys.stdin

try:
    sys.stdin = _BrokenStdin()

    # Import via the package entry point
    from src.env_check import is_interactive

    actual = is_interactive()
    # If we reach here, the function returned a value instead of raising.
    # That means either _BrokenStdin.isatty() didn't raise, or the function
    # caught the exception. Either way, the bug (exception propagation) is
    # not confirmed.
    print(f"NOT CONFIRMED — function returned {actual!r}; expected exception propagation")
except Exception as e:
    # The bug IS confirmed: is_interactive() propagated the exception instead
    # of returning False as the spec requires.
    print(f"CONFIRMED — actual: {type(e).__name__}: {e} | expected: False")
finally:
    sys.stdin = _original_stdin
```

### Probe Output

```
CONFIRMED — actual: OSError: input/output error — underlying file descriptor closed | expected: False
```
