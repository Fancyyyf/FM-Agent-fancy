# Bug Report: _prompt_backend

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/_prompt_backend.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a non-empty string that is one of: 'opencode', 'auto', 'codex-cli', or 'claude-cli'. The returned value corresponds to the user's confirmed choice from the displayed backend selection and is the first user-provided input that maps to a valid backend identifier. The function does not return until a valid selection is obtained.

---

### Actual Behavior

After execution, the menu lines have been printed to standard output. If the value read by `_prompt('Select', '1')` (defaulting to '1' on empty input) is `'1'`, `'2'`, `'3'`, or `'4'`, the function returns the corresponding backend string: `'opencode'`, `'auto'`, `'codex-cli'`, or `'claude-cli'` respectively. Otherwise, the function raises `ConfigWizardError` with the message `'Backend selection must be 1, 2, 3, or 4.'`.

---

## Code Evidence

Line 15:     try:
Line 16:         return backends[selected]
Line 17:     except KeyError as exc:
Line 18:         raise ConfigWizardError("Backend selection must be 1, 2, 3, or 4.") from exc

---

## Trigger Condition

The specification requires the function to not return until a valid selection is obtained, meaning it must repeatedly prompt. The code instead raises ConfigWizardError on any invalid input, terminating without retrying, which violates the 'does not return until a valid selection is obtained' contract.

---

## How to trigger the bug

Provide an invalid input (not 1, 2, 3, or 4) to the backend selection prompt. The function raises `ConfigWizardError` instead of reprompting the user.

### Inputs

| Parameter | Value |
|-----------|-------|
| `_prompt` return value | `"5"` (invalid — not in backends dict) |

### Expected (spec-correct) Output

Reprompt the user until a valid input is provided. For example, if the first input is `"5"` (invalid) and the second is `"1"` (valid), return `"opencode"`.

### Actual (buggy) Output

`ConfigWizardError: Backend selection must be 1, 2, 3, or 4.`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, 'src')
from configure_llm import _prompt_backend, ConfigWizardError
from unittest import mock

# Simulate entering "5" at the backend selection prompt
with mock.patch('configure_llm._prompt', return_value='5'):
    result = _prompt_backend()
# actual (buggy) output: ConfigWizardError("Backend selection must be 1, 2, 3, or 4.")
# expected (correct) output: reprompt until valid, then return backend string
```

---

## Probe Script

```python
"""Probe script for bug: _prompt_backend raises ConfigWizardError on invalid input
instead of reprompting until a valid selection is obtained."""

import io
import sys
from unittest import mock

sys.path.insert(0, 'src')
import configure_llm


def main() -> None:
    mock_prompt = mock.MagicMock(side_effect=["5", "1"])

    suppressed = io.StringIO()
    error = None
    actual = None

    with mock.patch.object(configure_llm, '_prompt', mock_prompt):
        with mock.patch('sys.stdout', suppressed):
            try:
                actual = configure_llm._prompt_backend()
            except configure_llm.ConfigWizardError as exc:
                error = exc
            except Exception as exc:
                error = exc

    if error is not None:
        if isinstance(error, configure_llm.ConfigWizardError):
            print('CONFIRMED - bug reproduced: function terminated with error on invalid input')
            print(f'  Error: {error}')
            print('  Expected: reprompt until valid input (spec: "does not return until valid")')
            print('  Actual: raised ConfigWizardError on first invalid input "5"')
        else:
            print(f'ERROR: {error}')
    else:
        expected = 'opencode'
        if actual == expected:
            print('NOT CONFIRMED - function reprompted and returned correct result')
            print(f'  Result: {actual!r} (expected {expected!r} for input "1")')
        else:
            print(f'NOT CONFIRMED - unexpected result: {actual!r} (expected {expected!r})')


if __name__ == '__main__':
    main()
```

### Probe Output

```
CONFIRMED - bug reproduced: function terminated with error on invalid input
  Error: Backend selection must be 1, 2, 3, or 4.
  Expected: reprompt until valid input (spec: "does not return until valid")
  Actual: raised ConfigWizardError on first invalid input "5"
```
