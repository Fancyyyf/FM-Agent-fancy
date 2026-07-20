# Bug Report: command_argv

**Source file:** `src/cli_backend.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When command has an `argv` attribute whose value is a list of strings:
    returns that list object (the same reference)  it is the caller's
    responsibility that the returned list contains only strings
  - When command is a string: returns a new single-element list containing
    that string
  - When command is any other iterable of strings: returns a new list whose
    elements are the strings yielded by iterating over command, preserving
    iteration order
  - The returned value is always a list of strings  every element is a str
  - Returns a list in all cases  no exceptions are raised for any valid
    input type

---

### Actual Behavior

The function returns a list of strings. If 'command' is an instance of AgentCommand, the returned list equals 'command.argv'. Otherwise, it equals 'list(command)'. Formally: (isinstance(command, AgentCommand)  result = command.argv)  (isinstance(command, AgentCommand)  result = list(command))  e : (e  result  type(e) = str)

---

## Code Evidence

Line 2: if isinstance(command, AgentCommand):; Line 4: return list(command)

---

## Trigger Condition

The specification requires that any input with an 'argv' attribute containing a list of strings returns that same list object. The code only does this for instances of AgentCommand. For any other object that has 'argv' but is not an AgentCommand instance, the code calls list(command), which may raise a TypeError (if the object is not iterable) or return a new list (if iterable), thus violating the required behavior and the 'no exceptions' guarantee.

---

## How to trigger the bug

A non-AgentCommand object that carries an `argv` attribute (a list of strings) triggers a `TypeError` because `command_argv` falls through to `list(command)`, and the object is not iterable. The spec requires the `argv` list to be returned directly (same reference) with no exceptions.

### Inputs

| Parameter | Value |
|-----------|-------|
| command | A `FakeCommand` instance with class attribute `argv = ['arg1', 'arg2']` (not iterable, not an `AgentCommand`) |

### Expected (spec-correct) Output

`['arg1', 'arg2']` (the same list object as `FakeCommand.argv`)

### Actual (buggy) Output

`TypeError: 'FakeCommand' object is not iterable`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.cli_backend import command_argv

class FakeCommand:
    argv = ['arg1', 'arg2']

command_argv(FakeCommand())
# actual (buggy) output: TypeError: 'FakeCommand' object is not iterable
# expected (correct) output: ['arg1', 'arg2'] (same reference)
```

---

## Probe Script

```python
"""Probe script for bug: src--cli_backend-py--command_argv"""

import sys
import os

# Ensure the repo root is on sys.path so the 'src' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from src.cli_backend import command_argv

    # An object that has an `argv` attribute (list of strings) but is NOT an AgentCommand.
    # The spec says it should return the same argv list object.
    # The code will fall through to `list(command)`, which raises TypeError since
    # FakeCommand instances are not iterable.
    class FakeCommand:
        argv = ['arg1', 'arg2']

    cmd = FakeCommand()
    result = command_argv(cmd)

    # If we reach here (no exception), the code DID iterate (possibly returning wrong results)
    expected = FakeCommand.argv
    passed = result is not expected  # Bug: should be same reference, but isn't
    if passed:
        print(f'CONFIRMED — actual: {result!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {result!r}')
except TypeError as e:
    # The bug triggers TypeError, which the spec says should never happen
    print(f'CONFIRMED — TypeError raised: {e}')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — TypeError raised: 'FakeCommand' object is not iterable
```
