# Bug Report: _check_oh_my_openagent

**Source file:** `fm_agent/extracted_functions/src/env_check-py/_check_oh_my_openagent.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns (True, None) when the `oh-my-openagent` command is available and executable via `bunx`.
  - Returns (False, str) when the `oh-my-openagent` command is not available or the check times out.
    The returned string is a fixed error message.
  - The function does not raise exceptions to its caller; all failure modes are captured as (False, str).

---

### Actual Behavior

The function returns a tuple (success, message). If the subprocess call to ['bunx', 'oh-my-openagent', '--version'] completes without raising an exception, the return value is (True, None). If any exception occurs during that call (e.g., timeout, file not found), the return value is (False, 'oh-my-openagent is not installed (bunx unavailable or timed out)'). No exception escapes the function. Formal logic: let result be the value returned by _check_oh_my_openagent. Then (result = (True, None))  (subprocess.run(['bunx', 'oh-my-openagent', '--version'], capture_output=True, text=True, timeout=10) did not raise an exception)  (result = (False, 'oh-my-openagent is not installed (bunx unavailable or timed out)'))  (the same subprocess.run call raised an exception).

---

## Code Evidence

Line 4: subprocess.run(
            ["bunx", "oh-my-openagent", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        Line 8: return True, None

---

## Trigger Condition

The code catches exceptions but never inspects the subprocess return code. If 'oh-my-openagent' is not installed, bunx may still execute and exit with a non-zero status, which is not an exception, so the function mistakenly reports success (True, None) when the specification demands (False, str) for an unavailable command.

---

## How to trigger the bug

The function calls `subprocess.run(["bunx", "oh-my-openagent", "--version"], capture_output=True, text=True, timeout=10)` but only checks for exceptions — it never inspects `returncode`. Since `check=False` by default, a non-zero exit code does not raise an exception. If `bunx` is present but `oh-my-openagent` fails to run (e.g., package not found, installation failure, network error during `bunx` fetch), `subprocess.run` returns a `CompletedProcess` with non-zero `returncode`, no exception is raised, and the function incorrectly returns `(True, None)`.

### Inputs

| Parameter | Value |
|-----------|-------|
| (none) | The function takes no arguments; it hard-codes the command `["bunx", "oh-my-openagent", "--version"]` |

### Expected (spec-correct) Output

`(False, "oh-my-openagent is not installed (bunx unavailable or timed out)")` or a similar error string when the command is not available

### Actual (buggy) Output

`(True, None)` — the subprocess completed (did not raise), so the function assumes success without checking `returncode`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())

import subprocess as sp_module

# Simulate bunx running but oh-my-openagent failing (non-zero exit, no exception)
class FakeCompletedProcess:
    def __init__(self):
        self.returncode = 1
        self.stdout = ''
        self.stderr = 'error: package "oh-my-openagent" not found'

original_run = sp_module.run
sp_module.run = lambda *a, **kw: FakeCompletedProcess()

from src.env_check import _check_oh_my_openagent
success, msg = _check_oh_my_openagent()
print(f"Result: ({success}, {msg!r})")
# actual (buggy) output: (True, None)
# expected (correct) output: (False, '<error message>')

sp_module.run = original_run
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root (cwd) is on sys.path so 'src' is importable
sys.path.insert(0, os.getcwd())

import subprocess as sp_module

# Save original before patching
_original_run = sp_module.run


class _FakeCompletedProcess:
    """Simulates bunx running but oh-my-openagent not found."""
    def __init__(self):
        self.returncode = 1
        self.stdout = ''
        self.stderr = 'error: package "oh-my-openagent" not found'


def _fake_run(args, **kwargs):
    return _FakeCompletedProcess()


# Monkey-patch so the function-under-test gets a non-zero returncode
# without an exception — exactly what triggers the bug.
sp_module.run = _fake_run

try:
    from src.env_check import _check_oh_my_openagent

    success, msg = _check_oh_my_openagent()

    # Spec claim: Returns (False, str) when command is not available.
    # Bug: returns (True, None) because only exceptions are caught,
    #      not non-zero return codes.
    expected_success = False
    expected_msg_is_str = True

    bug_confirmed = (
        success == True           # should be False — buggy
        and msg is None           # should be a string — buggy
    )

    if bug_confirmed:
        print(f'CONFIRMED — actual: (success={success}, msg={msg!r}) '
              f'| expected: (success=False, msg=<error string>)')
    else:
        print(f'NOT CONFIRMED — actual matched expected: '
              f'(success={success}, msg={msg!r})')

except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    sys.exit(1)
finally:
    sp_module.run = _original_run
```

### Probe Output

```
CONFIRMED — actual: (success=True, msg=None) | expected: (success=False, msg=<error string>)
```
