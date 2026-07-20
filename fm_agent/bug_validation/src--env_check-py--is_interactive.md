# Bug Report: is_interactive

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/env_check-py/is_interactive.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns True when the standard input stream (stdin) is attached to a terminal device,
    meaning the calling process can receive interactive user input via stdin.
  - Returns False when stdin is not attached to a terminal (e.g., piped input,
    redirection from a file, or non-TTY execution environment).
  - The return value does not depend on any mutable state and is determined solely by
    the process's file descriptor table at the time of the call.

---

### Actual Behavior

If `sys` is not defined, a `NameError` is raised. If `sys.stdin` does not have an `isatty` attribute, an `AttributeError` is raised. Otherwise, the function returns `True` if standard input is a terminal (TTY), `False` otherwise. Formally: normal postcondition: `result == sys.stdin.isatty()`; exceptional postconditions: `<NameError, 'sys'>` or `<AttributeError, 'isatty'>`.

---

## Code Evidence

Line 2: return sys.stdin.isatty()

---

## Trigger Condition

The code raises a NameError because 'sys' is not defined, while the specification requires the function to always return True or False based solely on the file descriptor table. The code's behavior depends on mutable global state (the presence of 'sys') and fails to meet the specification when that state is not set.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| (none)    | Removed `sys` from the module's global namespace before calling `is_interactive()` |

### Expected (spec-correct) Output

`True` or `False` — determined solely by whether stdin is a TTY (based on the process's file descriptor table).

### Actual (buggy) Output

`NameError: name 'sys' is not defined` — the function crashes because `sys` has been removed from the module's mutable global namespace, demonstrating that the implementation depends on mutable state (the presence of `sys`) rather than solely on the file descriptor table as the specification requires.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
sys.path.insert(0, '.')
import src.env_check as env_check

# Remove sys from the module's global namespace
del env_check.sys

# Call is_interactive — it will raise NameError because 'sys' is gone
env_check.is_interactive()
# actual (buggy) output: NameError: name 'sys' is not defined
# expected (correct) output: True or False based on file descriptor table
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on sys.path so 'src' is importable
# This probe is at fm_agent/bug_validation/probe_<bug_id>.py
# Repo root is 2 levels up
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

try:
    import src.env_check as env_check

    # The bug: is_interactive() depends on 'sys' being in the module's global namespace.
    # The spec says the return value must not depend on any mutable state.
    # By removing 'sys' from the module dict, we test whether the function
    # truly only depends on the file descriptor table (as the spec requires)
    # or depends on mutable global state (the presence of 'sys').
    del env_check.sys

    result = env_check.is_interactive()
    # If we get here, 'sys' was somehow still accessible
    print(f"NOT CONFIRMED — is_interactive() returned {result!r} even after removing sys from module globals")
except NameError as e:
    print(f"CONFIRMED — is_interactive() raised NameError after removing sys from module globals: {e}")
except AttributeError as e:
    print(f"CONFIRMED — is_interactive() raised AttributeError: {e}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — is_interactive() raised NameError after removing sys from module globals: name 'sys' is not defined
```
