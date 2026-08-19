# Bug Report: _spec_task_exit_code

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/verification-py/_spec_task_exit_code.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns the integer exit code of the execution represented by handle when the execution has reached a terminal state, or None when it has not. When handle has a 'returncode' attribute, its value is returned as the exit code. When handle has a 'done' method that returns True, the exit code is: the integer result of the handle's execution when that result is an integer; 0 when the result is a non-integer non-exceptional value; or 1 when the execution raised an exception. Returns None in all other cases.

---

### Actual Behavior

The function returns the exit status of `handle` as an integer or `None` without modifying `handle`. 

Specifically, the return value is determined as follows:
- If `handle` has a `returncode` attribute, then `handle.returncode` is returned (which may be an integer or `None`).
- Else if `handle` has a `done` method and `handle.done()` is `True`:
    - If `handle.result()` returns an integer `v`, then `v` is returned.
    - If `handle.result()` returns a non-integer value, then `0` is returned.
    - If `handle.result()` raises an `Exception`, then `1` is returned.
- Otherwise `None` is returned.

Formally:
Let `H` be the initial value of `handle` (unchanged).
\result = 
    H.returncode   if hasattr(H, 'returncode')
    else (
        if hasattr(H, 'done') and H.done() then
            ( let r = opaque H.result() in (r if isinstance(r, int) else 0) )
            unless Exception raised, in which case 1
        else None
    )
where `opaque H.result()` denotes the value returned by `H.result()` if no exception occurs.

---

## Code Evidence

Line 5: if hasattr(handle, "done") and handle.done():

---

## Trigger Condition

The specification requires returning None in all cases except when the handle has a 'returncode' attribute or the done() method returns True. If done() raises an exception, it does not return True, so the specification implies None should be returned; the code does not catch exceptions from done(), causing a violation.

---

## How to trigger the bug

The function `_spec_task_exit_code(handle)` calls `handle.done()` without exception handling on line 55. When `handle` has a `done` method that raises an exception, the spec requires returning `None` (since `done()` did not return `True`), but the code propagates the exception instead.

### Inputs

| Parameter | Value |
|-----------|-------|
| `handle` | An object with a `done()` method that raises `RuntimeError("done() failed unexpectedly")`, and without a `returncode` attribute |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`RuntimeError("done() failed unexpectedly")` is raised (exception propagates)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.verification import _spec_task_exit_code

class FailingDoneHandle:
    def done(self):
        raise RuntimeError("done() failed unexpectedly")

handle = FailingDoneHandle()
# spec requires: _spec_task_exit_code(handle) -> None
# actual (buggy) output: RuntimeError is raised
result = _spec_task_exit_code(handle)  # raises RuntimeError
```

---

## Probe Script

```python
import sys
import os

# Add the repo root to sys.path so 'src' can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.verification import _spec_task_exit_code

    class FailingDoneHandle:
        """Handle where done() raises an exception.

        Per spec: when done() raises, it does not return True,
        so None should be returned. The bug is that handle.done()
        is called without exception handling on line 55.
        """
        def done(self):
            raise RuntimeError("done() failed unexpectedly")

    handle = FailingDoneHandle()

    # handle has no 'returncode' attribute -> skips first if
    # handle has 'done' attribute -> enters second if
    # handle.done() raises -> spec says return None, code propagates exception
    actual = _spec_task_exit_code(handle)
    # If we reach here, the exception was caught somewhere — bug NOT confirmed
    print(f'NOT CONFIRMED -- _spec_task_exit_code returned {actual!r}')
except Exception as e:
    # Exception propagated — bug CONFIRMED (spec requires None)
    print(f'CONFIRMED -- done() exception propagated as: {type(e).__name__}: {e}')
    print(f'(spec requires returning None when done() raises)')
```

### Probe Output

```
CONFIRMED -- done() exception propagated as: RuntimeError: done() failed unexpectedly
(spec requires returning None when done() raises)
```
