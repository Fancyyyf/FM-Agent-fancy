# Bug Report: command_display

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/cli_backend-py/command_display.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a single-line string. The returned string begins with the result of shell-quoting and whitespace-joining every element of command_argv(command)  that is, each element is individually escaped such that the concatenation is a valid shell command-line representation. When command_stdin(command) is not None, the literal suffix " <stdin>" is appended to the result; when command_stdin(command) is None, no suffix is appended. The returned string contains no embedded newline characters.

---

### Actual Behavior

The function returns a string representation of the command suitable for display. If command_stdin(command) is not None, the returned string ends with " <stdin>"; otherwise it consists solely of the shell-escaped command arguments. No exceptions are raised, and no side effects occur. Formally:

Let argv = command_argv(command) and stdin = command_stdin(command).
Then _result = shlex.join(argv) + (" <stdin>" if stdin is not None else "").

---

## Code Evidence

Line 4: return shlex.join(argv) + suffix

---

## Trigger Condition

shlex.join does not filter out newline characters from arguments; thus, if any argument contains a newline, the result contains an embedded newline, contradicting the 'no embedded newline characters' requirement of condition B.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| command.argv | `["echo", "line1\nline2"]` (a literal newline between "line1" and "line2") |
| command.stdin | `None` |

### Expected (spec-correct) Output

A single-line string with no embedded newline characters, e.g. `"echo 'line1\\nline2'"` (with newline escaped) or `"echo 'line1 line2'"` (with newline removed).

### Actual (buggy) Output

`"echo 'line1\nline2'"` — contains a literal newline character between "line1" and "line2" inside the single-quoted argument.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys, os
sys.path.insert(0, os.getcwd())
from src.cli_backend import command_display, AgentCommand

cmd = AgentCommand(argv=["echo", "line1\nline2"])
result = command_display(cmd)
print(repr(result))
# actual (buggy) output: "echo 'line1\nline2'"  (newline is embedded literally)
# expected (correct) output: a string with no embedded newline characters
```

---

## Probe Script

```python
import sys
import os

# Ensure the project root is on the Python path so 'src' can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    from src.cli_backend import command_display, AgentCommand

    # An argument containing a literal newline character should cause
    # command_display to return a string with an embedded newline, which
    # violates the spec claim: "The returned string contains no embedded
    # newline characters."

    cmd = AgentCommand(argv=["echo", "line1\nline2"])
    result = command_display(cmd)

    # Bug confirmed if the result has a newline (spec prohibits it)
    has_newline = "\n" in result

    if has_newline:
        print(f"CONFIRMED — result contains embedded newline: {result!r}")
    else:
        print(f"NOT CONFIRMED — no embedded newline in result: {result!r}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — result contains embedded newline: "echo 'line1\nline2'"
```
