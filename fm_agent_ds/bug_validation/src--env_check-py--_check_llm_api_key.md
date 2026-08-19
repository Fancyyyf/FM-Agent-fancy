# Bug Report: _check_llm_api_key

**Source file:** `fm_agent/extracted_functions/src/env_check-py/_check_llm_api_key.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns (True, None) when the configured API key string is non-empty (after stripping whitespace) and is not among a fixed set of known placeholder or default values (strings that appear in unconfigured .env.example templates). Returns (False, error_message) when the API key is empty, falsy, or equals one of the fixed placeholder values. The error_message is a non-empty string indicating the API key is not configured. The function has no side effects.

---

### Actual Behavior

After execution, the function returns a tuple (ok, msg). ok is True if and only if config.LLM_API_KEY is a truthy string and is not one of the placeholder values: the empty string, 'YOUR_LLM_API_KEY', or 'sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'. msg equals the string 'LLM_API_KEY is not set in .env file' when ok is False, and msg is None when ok is True. The state of config is unmodified, and no exceptions are raised. Formally: let key = config.LLM_API_KEY; let S = {'', 'YOUR_LLM_API_KEY', 'sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}. Then ok := (key  None  key  S)  msg := ('LLM_API_KEY is not set in .env file' if ok else None).

---

## Code Evidence

Line 2:     ok = bool(config.LLM_API_KEY and config.LLM_API_KEY not in (
Line 3:         "", "YOUR_LLM_API_KEY",
Line 4:         "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
Line 5:     ))

---

## Trigger Condition

The code does not strip whitespace from the API key before testing emptiness or placeholder membership. As a result, a whitespace-only string is truthy and not equal to any listed placeholder, so it is treated as valid (returns True). The specification requires stripping whitespace, after which such a key becomes empty and should be rejected with an error message.

---

## How to trigger the bug

The bug is triggered when `config.LLM_API_KEY` is a whitespace-only string (e.g., `"   "`). The function treats it as a valid key because whitespace-only strings are truthy and don't match any placeholder value. The spec requires stripping whitespace first, which would reduce it to the empty string `""` — a known placeholder — causing rejection.

### Inputs

| Parameter | Value |
|-----------|-------|
| config.LLM_API_KEY | `"   "` |

### Expected (spec-correct) Output

`(False, "LLM_API_KEY is not set in .env file")`

### Actual (buggy) Output

`(True, None)`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.env_check import _check_llm_api_key

class MockConfig:
    def __init__(self, api_key):
        self.LLM_API_KEY = api_key

config = MockConfig("   ")
ok, msg = _check_llm_api_key(config)
# actual (buggy) output: (True, None)
# expected (correct) output: (False, "LLM_API_KEY is not set in .env file")
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so that `src` is importable
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

class MockConfig:
    """Minimal config-like object exposing LLM_API_KEY as an attribute."""
    def __init__(self, api_key):
        self.LLM_API_KEY = api_key

try:
    from src.env_check import _check_llm_api_key

    # Test: whitespace-only API key should be rejected after stripping
    config = MockConfig("   ")
    ok, msg = _check_llm_api_key(config)

    actual = (ok, msg)
    # Spec says: strip whitespace → key becomes "" → in placeholders → (False, error_msg)
    expected = (False, "LLM_API_KEY is not set in .env file")
    # Bug is confirmed if actual != expected (actual erroneously returns True)
    passed = actual != expected

    if passed:
        print(f'CONFIRMED — actual: {actual!r} | expected: {expected!r}')
    else:
        print(f'NOT CONFIRMED — actual matched expected: {actual!r}')

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: (True, None) | expected: (False, 'LLM_API_KEY is not set in .env file')
```
