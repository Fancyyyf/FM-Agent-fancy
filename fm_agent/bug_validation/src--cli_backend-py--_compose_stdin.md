# Bug Report: _compose_stdin

**Source file:** `src/cli_backend.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- When files is empty, returns None
  - When files is non-empty, returns a string that begins with a directive
    to read the listed files, enumerates each file path on a separate line,
    and appends the prompt text after a blank line

---

### Actual Behavior

The function returns a string. If the input list `files` is empty, the returned string is identical to the input `prompt`. Otherwise, the returned string is `'Read these file(s) before acting:\n' + '\n'.join('- ' + path for path in files) + '\n\n' + prompt`. The order of the file paths in the output matches the order in the input list. The function has no side effects and does not modify the inputs.

---

## Code Evidence

Line 2:     if not files:
Line 3:         return prompt

---

## Trigger Condition

Condition B specifies that when files is empty, the function must return None, but the code returns the prompt string.

---

## How to trigger the bug

The function `_compose_stdin` is called from `build_agent_command` in `src/cli_backend.py` with `files or []`. When `files` is `None` or empty, the function receives an empty list and returns the raw `prompt` string instead of `None`.

### Inputs

| Parameter | Value |
|-----------|-------|
| `prompt` | `"Hello, world!"` |
| `files` | `[]` (empty list) |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`"Hello, world!"`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
from src.cli_backend import _compose_stdin

# Bug: should return None but returns the prompt string
result = _compose_stdin("Hello, world!", [])
# actual (buggy) output: "Hello, world!"
# expected (correct) output: None
```

---

## Probe Script

```py
import sys
sys.path.insert(0, '/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot')

try:
    from src.cli_backend import _compose_stdin

    # Trigger: files is an empty list — spec says return None, code returns prompt
    actual   = _compose_stdin("Hello, world!", [])
    expected = None
    passed   = actual != expected

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if passed:
    print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — actual: 'Hello, world!' | expected: None
```
