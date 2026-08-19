# Bug Report: _check_oh_my_openagent

**Source file:** `src/env_check.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns (True, None) when oh-my-openagent is reachable via bunx and responds to its version flag within 10 seconds, indicating the tool is installed and executable. Returns (False, "oh-my-openagent is not installed (bunx unavailable or timed out)") when oh-my-openagent cannot be invoked via bunx for any reason, including bunx itself being unavailable, the tool not being installed, or the invocation exceeding 10 seconds. The function produces no side effects  it does not create, modify, or delete any files.

---

### Actual Behavior

After the function call, one of the following holds:
1. If the import of `subprocess` failed, an `ImportError` (or subclass) was raised and the function did not return. No tuple was produced.
2. Otherwise, the function returned a 2-tuple `(result, message)` where:
   - If the subprocess run completed without raising any exception, then `result` is `True` and `message` is `None`.
   - If any exception occurred during `subprocess.run(...)` (including `CalledProcessError`, `FileNotFoundError`, `TimeoutExpired`, etc.), then `result` is `False` and `message` equals the string `"oh-my-openagent is not installed (bunx unavailable or timed out)"`.

Formally, let `S` be the state after the call, `R` the return value, and `E` any uncaught exception.
- `(E = none)  (import subprocess succeeded)`
- `(E = none)  (R is a 2-tuple)  (R[0]  {True, False})`
- `(E = none  R[0] = True)  (R[1] is None)  (subprocess.run completed without exception)`
- `(E = none  R[0] = False)  (R[1] = "oh-my-openagent is not installed (bunx unavailable or timed out)")  (subprocess.run raised an exception)`
- If `import subprocess` raised an exception, then `E` is that exception and no return value exists.

---

## Code Evidence

Line 4: subprocess.run(...); Line 8: return True, None

---

## Trigger Condition

The code does not check the subprocess return code or output. A non-zero exit status (e.g., when oh-my-openagent is missing) causes the function to return True, violating the specification which requires False for any failure to invoke the tool.

---

## How to trigger the bug

The function uses `subprocess.run()` without `check=True`, so a non-zero exit code from `bunx oh-my-openagent --version` does not raise an exception. The code falls through to `return True, None` even though the tool is unavailable. The mock in the probe simulates this scenario: `subprocess.run` returns a `CompletedProcess` with `returncode=1` and no exception, yet the function reports success.

### Inputs

| Parameter | Value |
|-----------|-------|
| (no parameters) | The function takes no arguments; it invokes `bunx oh-my-openagent --version` internally |

### Expected (spec-correct) Output

`(False, "oh-my-openagent is not installed (bunx unavailable or timed out)")`

### Actual (buggy) Output

`(True, None)`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import subprocess

# When oh-my-openagent is not installed, bunx exits non-zero.
# subprocess.run() without check=True does NOT raise on non-zero exit.
from src.env_check import _check_oh_my_openagent
result, message = _check_oh_my_openagent()
# actual (buggy) output: (True, None)
# expected (correct) output: (False, "oh-my-openagent is not installed (bunx unavailable or timed out)")
```

---

## Probe Script

```python
"""Probe for _check_oh_my_openagent bug: subprocess.run without check=True
silently accepts non-zero exit codes, causing the function to return (True, None)
when oh-my-openagent is actually unavailable.

Bug ID: src--env_check-py--_check_oh_my_openagent
"""

import sys
import os
import tempfile

# Ensure the repo root is on sys.path so the src package is importable.
# The probe runs with CWD=repo_root, but we capture it before chdir.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Use a fresh temp workspace for any file I/O (FM-Agent self-validation rule)
WORKSPACE = tempfile.mkdtemp(prefix="probe_oh_my_openagent_")
os.chdir(WORKSPACE)

# Patch subprocess.run to simulate a non-zero exit without raising an exception.
# This mimics: bunx is available, but oh-my-openagent fails (e.g. not installed).
import subprocess as _real_subprocess

_original_run = _real_subprocess.run


class _MockCompletedProcess:
    """Simulates a subprocess that ran but exited non-zero."""
    returncode = 1
    stdout = ""
    stderr = "error: package 'oh-my-openagent' not found"


def _mock_run(*args, **kwargs):
    return _MockCompletedProcess()


_real_subprocess.run = _mock_run

try:
    # Import through the public package entry point
    from src.env_check import _check_oh_my_openagent

    result, message = _check_oh_my_openagent()

    if result is True and message is None:
        print(
            "CONFIRMED — Bug reproduced: function returned (True, None) "
            "even though subprocess exited with code 1. "
            "Spec requires (False, 'oh-my-openagent is not installed "
            "(bunx unavailable or timed out)') when the tool cannot be invoked."
        )
    elif result is False:
        print(
            f"NOT CONFIRMED — function correctly returned "
            f"(False, {message!r}) for a failed subprocess"
        )
    else:
        print(
            f"NOT CONFIRMED — unexpected result: ({result!r}, {message!r})"
        )

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)

finally:
    _real_subprocess.run = _original_run
```

### Probe Output

```
CONFIRMED — Bug reproduced: function returned (True, None) even though subprocess exited with code 1. Spec requires (False, 'oh-my-openagent is not installed (bunx unavailable or timed out)') when the tool cannot be invoked.
```
