# Bug Report: run

**Source file:** `src/env_check-py/run.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Each failing check produces a warning logged via logging.warning in the format
  "[!] <label>: <message>" where label identifies the check and message is the
  reason for failure.

---

### Actual Behavior

The code produces warning messages with two leading spaces: "  [!] <label>: <message>", which does not match the required format.

---

## Code Evidence

Line 30: lines.append(f"  [!] {label}: {msg}")

---

## Trigger Condition

The specification requires each failing check to produce a warning in the exact format '[!] <label>: <message>'. The code prepends two spaces, resulting in '  [!] <label>: <message>', which does not match the required format.

---

## How to trigger the bug

Call `run(proj_dir, config)` with a config that causes at least one environment check to fail (e.g., an empty `LLM_API_KEY`). The resulting `logging.warning` messages will contain two leading spaces before `[!]`, violating the specification's required format.

### Inputs

| Parameter | Value |
|-----------|-------|
| `proj_dir` | A temporary directory path |
| `config.LLM_API_KEY` | `""` (empty string) |

### Expected (spec-correct) Output

`[!] LLM API Key configured: LLM_API_KEY is not set in .env file`

### Actual (buggy) Output

`  [!] LLM API Key configured: LLM_API_KEY is not set in .env file`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
import logging
import tempfile

# Capture logging.warning calls
captured_warnings = []
_original_warning = logging.warning
def _capture_warning(msg, *args, **kwargs):
    if args:
        msg = msg % args
    captured_warnings.append(str(msg))
logging.warning = _capture_warning

sys.path.insert(0, os.getcwd())
from src.env_check import run

class FakeConfig:
    LLM_API_KEY = ""

tmpdir = tempfile.mkdtemp()
run(tmpdir, FakeConfig())

logging.warning = _original_warning

for msg in captured_warnings:
    if msg.startswith("  [!]"):
        print(f"BUG: warning has leading spaces: {msg!r}")
        # actual (buggy) output: '  [!] LLM API Key configured: LLM_API_KEY is not set in .env file'
        # expected (correct) output: '[!] LLM API Key configured: LLM_API_KEY is not set in .env file'
```

---

## Probe Script

```python
import sys
import os
import logging
import tempfile
import traceback

# Ensure the repo root is on sys.path so 'src' is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Capture logging.warning calls before importing the module
captured_warnings = []
_original_warning = logging.warning

def _capture_warning(msg, *args, **kwargs):
    if args:
        msg = msg % args
    captured_warnings.append(str(msg))

logging.warning = _capture_warning

try:
    from src.env_check import run

    class _FakeConfig:
        LLM_API_KEY = ""  # empty key triggers the LLM key check to fail

    tmpdir = tempfile.mkdtemp()
    result = run(tmpdir, _FakeConfig())

    logging.warning = _original_warning

    # Check for the bug: warning should be "[!] <label>: <message>" per spec,
    # but code produces "  [!] <label>: <message>" with two leading spaces
    bug_confirmed = False
    actual_msg = None
    for msg in captured_warnings:
        if msg.startswith("  [!]"):
            bug_confirmed = True
            actual_msg = msg
            break

    if bug_confirmed:
        print(f"CONFIRMED — warning format has leading spaces: {actual_msg!r} | expected: '[!] <label>: <message>'")
    else:
        print(f"NOT CONFIRMED — no warning with leading spaces found")
        print(f"Captured warnings: {captured_warnings!r}")

except Exception as e:
    logging.warning = _original_warning
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — warning format has leading spaces: '  [!] LLM API Key configured: LLM_API_KEY is not set in .env file' | expected: '[!] <label>: <message>'
```
