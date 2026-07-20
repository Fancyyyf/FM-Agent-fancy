# Bug Report: _elp_argv

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/languages/erlang-py/_elp_argv.py`
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

The function returns a list of strings with no other side effects. The returned list is computed as follows: let env_val = os.environ.get('ELP_COMMAND', 'elp'); let stripped = env_val.strip(); let command = stripped if stripped else 'elp'; let posix = (os.name != 'nt'); let argv = shlex.split(command, posix=posix); then the return value is argv + ['server']. Since command is never empty, argv is never empty and the dead-code fallback to ['elp'] is unreachable.

---

## Code Evidence

Line 3: argv = shlex.split(command, posix=os.name != "nt")

---

## Trigger Condition

The specification states that the function returns a non-empty list of strings, but for invalid shell syntax (e.g., unbalanced quoting), shlex.split raises ValueError, causing the function to throw an exception instead of returning a list. This violates the implicit requirement that the function return a list for all possible environment values.

---

## How to trigger the bug

The function `_elp_argv()` reads the `ELP_COMMAND` environment variable and passes it through `shlex.split()`. When the environment variable contains a string with unbalanced quoting (e.g., `"unclosed`), `shlex.split()` raises a `ValueError` instead of returning a list. The specification requires the function to always return a non-empty list of strings, so this exception is a spec violation.

### Inputs

| Parameter | Value |
|-----------|-------|
| `ELP_COMMAND` (env var) | `"unclosed` |

### Expected (spec-correct) Output

A non-empty list of strings (function should handle the malformed input gracefully, e.g., by falling back to `["elp", "server"]`)

### Actual (buggy) Output

`ValueError: No closing quotation` — the function throws an exception instead of returning a list

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import os
os.environ["ELP_COMMAND"] = '"unclosed'

from src.languages.erlang import _elp_argv
try:
    result = _elp_argv()          # expected: non-empty list of strings
    print(f"returned: {result}")  # actual: ValueError is raised before this line
except ValueError as e:
    print(f"ValueError raised: {e}")
# actual (buggy) output: ValueError: No closing quotation
# expected (correct) output: ['"unclosed', 'server'] or ['elp', 'server']
```

---

## Probe Script

```python
"""Probe script for _elp_argv bug: shlex.split raises ValueError on unbalanced quoting."""
import os
import sys
import traceback

# Ensure the project root is on sys.path so the public entry-point import works
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Set ELP_COMMAND to a value with unbalanced quoting that triggers shlex.split ValueError
os.environ["ELP_COMMAND"] = '"unclosed'

try:
    from src.languages.erlang import _elp_argv

    actual = _elp_argv()
    if isinstance(actual, list) and len(actual) > 0:
        print(f"NOT CONFIRMED — function returned list: {actual!r}")
    else:
        print(f"CONFIRMED — function returned non-list or empty: {actual!r}")

except ValueError:
    # Spec: function must return a non-empty list of strings.
    # Actual: shlex.split raises ValueError on unbalanced quoting.
    print("CONFIRMED — shlex.split raised ValueError on unbalanced quoting (spec requires non-empty list)")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — shlex.split raised ValueError on unbalanced quoting (spec requires non-empty list)
```
