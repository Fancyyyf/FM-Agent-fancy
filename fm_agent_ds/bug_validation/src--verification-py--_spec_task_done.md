# Bug Report: _spec_task_done

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/verification-py/_spec_task_done.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns True if and only if handle is not None and the asynchronous task represented by handle has completed: for a Future object, done() returns True (the future is completed or cancelled); for a Popen object, poll() returns a non-None value (the process has terminated). Returns False if handle is None.

---

### Actual Behavior

The function returns a boolean indicating whether the task associated with `handle` is done. If `handle` is `None`, it returns `True`. If `handle` is a `subprocess.Popen` object, it returns `True` if and only if `handle.poll()` returns a non-None value (process has terminated), otherwise `False`. If `handle` is a `concurrent.futures.Future` object, it returns the result of `handle.done()`. The function never raises an exception under the given pre-condition. No side effects beyond the non-blocking queries `poll()` or `done()` occur. Formal: `(handle is None  result = True)  (handle  subprocess.Popen  result = (handle.poll()  None))  (handle  concurrent.futures.Future  result = handle.done())`

---

## Code Evidence

Line 7: return True

---

## Trigger Condition

Condition B requires returning False when handle is None, but the code returns True.

---

## How to trigger the bug

The function `_spec_task_done` falls through to `return True` on line 7 when the handle has neither a `poll` nor a `done` attribute. When `handle` is `None`, `hasattr(None, "poll")` is `False` and `hasattr(None, "done")` is `False`, so the function reaches the fallthrough and returns `True`. The specification requires `False` when `handle` is `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `handle` | `None` |

### Expected (spec-correct) Output

`False`

### Actual (buggy) Output

`True`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.verification import _spec_task_done

# actual (buggy) output: True
# expected (correct) output: False
print(_spec_task_done(None))
```

---

## Probe Script

```python
"""Probe script for bug: src--verification-py--_spec_task_done

The spec claims _spec_task_done returns False when handle is None,
but the code returns True (line 7: return True as the fallback).
"""
import sys
import os

# When run from repo root, the 'src' package should be importable.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.verification import _spec_task_done

    # Bug check: handle is None should return False per spec, but returns True.
    actual = _spec_task_done(None)
    expected = False  # what the spec requires

    passed = actual != expected  # True means the bug is reproduced

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')

        # Additional sanity: verify correct cases still work (Popen / Future)
        import concurrent.futures
        import subprocess
        import threading

        # Popen: running process should be "not done"
        proc = subprocess.Popen(['sleep', '0.1'])
        assert _spec_task_done(proc) is False, "running Popen should be not done"
        proc.wait()
        assert _spec_task_done(proc) is True, "completed Popen should be done"

        # Future: a not-yet-done future should be "not done"
        with concurrent.futures.ThreadPoolExecutor() as ex:
            barrier = threading.Barrier(2, timeout=5)
            def slow_task():
                barrier.wait()
                return 42
            fut = ex.submit(slow_task)
            assert _spec_task_done(fut) is False, "not-yet-completed future should be not done"
            barrier.wait()
            fut.result()
            assert _spec_task_done(fut) is True, "completed future should be done"

        print("CONFIRMED — additional sanity checks passed")
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: True | expected: False
CONFIRMED — additional sanity checks passed
```
