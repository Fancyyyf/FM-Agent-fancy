# Bug Report: _elp_argv

**Source file:** `src/languages/erlang.py` (extracted path: `src/languages/erlang-py/_elp_argv.py`)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a non-empty list of strings representing the argument vector used to
    launch the Erlang Language Platform server subprocess
  - The last element of the returned list is the string "server"
  - The returned value is deterministic across calls: given an unchanged value of
    the ELP_COMMAND environment variable and the same operating-system platform
    (POSIX vs non-POSIX), repeated calls return the same list
  - When the ELP_COMMAND environment variable changes, the returned list reflects
    the new command

---

### Actual Behavior

The function returns a list of strings, specifically the result of (shlex.split(settings.erlang.command.strip() or 'elp', posix=(os.name != 'nt')) or ['elp']) + ['server']. In natural language: the return value r is a nonempty list whose last element is 'server'. The prefix list is obtained by taking the stripped value of settings.erlang.command, defaulting to 'elp' if empty, splitting it into tokens via shlex.split (with posix mode true when os.name is not 'nt'), and using ['elp'] if that split yields an empty list. Formally:  r = _elp_argv()  r = (let c = settings.erlang.command.strip() in let cmd = c if c != '' else 'elp' in let parts = shlex.split(cmd, posix=(os.name != 'nt')) in (parts if parts else ['elp'])) + ['server'].

---

## Code Evidence

Line 2: command = settings.erlang.command.strip() or "elp"

---

## Trigger Condition

When ELP_COMMAND is not set, settings.erlang.command may be None. Calling .strip() on None raises AttributeError, so the function does not return a list of strings as required by the specification.

---

## How to trigger the bug

When `settings.erlang.command` is `None` (e.g., if the config object bypasses pydantic validation or is accessed before full initialization), the expression `settings.erlang.command.strip()` raises `AttributeError: 'NoneType' object has no attribute 'strip'`. The post-condition requires the function to return a non-empty list of strings, but it instead throws an unhandled exception.

In normal operation, pydantic's `ErlangCfg` model defaults `command` to the string `"elp"` and validates it as `str`, so the `None` state is normally prevented. However, the code at line 58 does not defensively guard against a `None` value, making it fragile if the config object is manipulated or dynamically constructed.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings.erlang.command` | `None` (bypassed pydantic validation) |

### Expected (spec-correct) Output

`['elp', 'server']` (or a valid argv list ending with `'server'`)

### Actual (buggy) Output

`AttributeError: 'NoneType' object has no attribute 'strip'`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from config import settings
from src.languages.erlang import _elp_argv

# Bypass pydantic validation to simulate command being None
object.__setattr__(settings.erlang, 'command', None)
_elp_argv()
# actual (buggy) output: AttributeError: 'NoneType' object has no attribute 'strip'
# expected (correct) output: ['elp', 'server']
```

---

## Probe Script

```python
"""Probe for _elp_argv bug: settings.erlang.command.strip() fails when command is None."""
import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, repo_root)

try:
    from config import settings
    from src.languages import erlang as erlang_module

    # Save original value
    orig = settings.erlang.command

    # Bypass pydantic validation to set command to None
    object.__setattr__(settings.erlang, 'command', None)

    try:
        result = erlang_module._elp_argv()
        # If we reach here, no AttributeError was raised
        print(f'NOT CONFIRMED — _elp_argv() returned {result!r} without error')
    except AttributeError as e:
        print(f'CONFIRMED — AttributeError raised when command is None: {e}')
    except Exception as e:
        print(f'ERROR — unexpected exception: {type(e).__name__}: {e}')
    finally:
        # Restore original value
        object.__setattr__(settings.erlang, 'command', orig)

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — AttributeError raised when command is None: 'NoneType' object has no attribute 'strip'
```
