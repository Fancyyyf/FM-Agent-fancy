# Bug Report: _spec_task_exit_code

**Source file:** `fm_agent/extracted_functions/src/verification-py/_spec_task_exit_code.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns an integer status code derived from the completed handle's
    outcome, or None when the handle type exposes no status-reporting
    mechanism
  - When the handle carries a direct exit-code attribute: returns its
    value (an integer or None) unchanged
  - When the handle resolves to a value: returns that value if it is
    an integer; returns 0 if the resolved value is of any non-integer
    type
  - When handle resolution raises any exception: returns 1

---

### Actual Behavior

Given the pre-condition that `handle` refers to a completed task (i.e., `_spec_task_done(handle) == True`), after `_spec_task_exit_code(handle)` finishes execution, it returns an integer exit code or `None` as follows:

- If `hasattr(handle, 'returncode')` evaluates to `True`, the return value is `handle.returncode`.
- Otherwise, if `hasattr(handle, 'done')` and `handle.done()` both evaluate to `True`:
  - The function attempts to evaluate `handle.result()`. If that call completes without raising an exception, then:
    - if `isinstance(result, int)` is `True`, the return value is `result`;
    - otherwise, the return value is `0`.
  - If `handle.result()` raises an exception (any `Exception`), the return value is `1`.
- Otherwise (neither a `returncode` attribute nor a `done` method that returns `True` exists), the function returns `None`.

Formal post-condition: Let `res` denote the return value of `_spec_task_exit_code(handle)` after the call. Then:

res =
  h.returncode                     if hasattr(h, 'returncode')
  else ( 1                         if h.result() raises Exception
         else ( r if isinstance(r, int) else 0 )
         where r = h.result() )    if hasattr(h, 'done')  h.done()
  else None

where `h` is the state of `handle` at function entry (and, by the pre-condition, the task it represents is known to have completed).

---

## Code Evidence

Line 9:         except Exception:

---

## Trigger Condition

The code only catches Exception subclasses. However, the specification requires returning 1 when handle resolution raises any exception, including non-Exception exceptions like KeyboardInterrupt or SystemExit. If result() raises KeyboardInterrupt, the code does not catch it and the call raises, violating the spec.

---

## How to trigger the bug

The code catches only `Exception` (line 59/34: `except Exception:`), but Python's exception hierarchy has `BaseException` as the root. `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` inherit directly from `BaseException`, not from `Exception`. When `handle.result()` raises a `BaseException` subclass that is not also an `Exception` subclass, the `except Exception:` handler is bypassed, and the exception propagates upward instead of returning `1` as the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| handle | An object with `done()` returning `True` and `result()` raising a `BaseException` (not `Exception`) subclass |

### Expected (spec-correct) Output

`1` (integer)

### Actual (buggy) Output

The `BaseException` propagates uncaught (the function does not return)

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())

from src.verification import _spec_task_exit_code

class BuggyHandle:
    def done(self):
        return True
    def result(self):
        raise KeyboardInterrupt()

handle = BuggyHandle()
try:
    code = _spec_task_exit_code(handle)
    # actual (buggy) output: KeyboardInterrupt propagates
    # expected (correct) output: 1
except KeyboardInterrupt:
    print("BUG: KeyboardInterrupt propagated instead of returning 1")
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on the path so that 'src' is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class CustomBaseException(BaseException):
    """Exception that inherits from BaseException, not Exception."""

try:
    from src.verification import _spec_task_exit_code

    class BuggyHandle:
        def done(self):
            return True

        def result(self):
            raise CustomBaseException("test probe exception")

    handle = BuggyHandle()
    try:
        actual = _spec_task_exit_code(handle)
        expected = 1
        passed = actual != expected
        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
    except CustomBaseException:
        # Bug confirmed: the exception propagated because except Exception
        # on line 59/34 only catches Exception subclasses, not BaseException.
        print(
            "CONFIRMED — CustomBaseException propagated (not caught "
            "by except Exception), expected return 1"
        )
    except BaseException as e:
        print(f"ERROR: unexpected: {type(e).__name__}: {e}")
        sys.exit(1)

except BaseException as e:
    print(f"ERROR: import/setup failed: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — CustomBaseException propagated (not caught by except Exception), expected return 1
```
