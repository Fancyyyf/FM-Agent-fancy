# Bug Report: _opencode_provider_config

**Source file:** `/tmp/fm_agent_wt_FM-Agent_xyeqtgt6/snapshot/fm_agent/extracted_functions/src/opencode_trace-py/_opencode_provider_config.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns None when any of api_key, base_url, name, or provider is falsy
    (i.e., an empty string, None, or otherwise evaluates to False).
  - When all of api_key, base_url, name, and provider are truthy, returns a
    dict that, when included in an OpenCode configuration, defines a valid
    provider.
  - The returned dict nests under a "provider" key, keyed by the value of the
    provider setting, and contains an npm adapter package name, a base URL, a
    model name, and an API key reference.
  - The npm adapter is chosen based on the api_style setting: the Anthropic SDK
    package when api_style is "anthropic", and an OpenAI-compatible SDK package
    otherwise.
  - The API key is specified as an environment-variable reference
    ({env:LLM_API_KEY}) rather than a literal key value.
  - The function has no side effects: it does not mutate any global state,
    perform I/O, or modify any passed-in arguments.
  - No exceptions are raised under normal operation.

---

### Actual Behavior

The function _opencode_provider_config() does not modify any global state (e.g., the settings object remains unchanged). Its return value is determined as follows: if any of the attributes settings.llm.api_key, settings.llm.base_url, settings.llm.name, or settings.llm.provider is falsy (None, empty string, etc.), the function returns None. Otherwise, it returns a dictionary with exactly one top-level key 'provider', whose value is a dictionary containing exactly one key equal to settings.llm.provider. That inner dictionary has the keys 'npm', 'options', and 'models'. The value of 'npm' is '@ai-sdk/anthropic' if settings.llm.api_style equals the string 'anthropic', else '@ai-sdk/openai-compatible'. The value of 'options' is a dictionary with keys 'baseURL' (set to settings.llm.base_url) and 'apiKey' (set to the literal string '{env:LLM_API_KEY}'). The value of 'models' is a dictionary with a single key settings.llm.name whose value is an empty dictionary {}. Formally:

let llm = settings.llm in
((llm.api_key  llm.base_url  llm.name  llm.provider)  result = None) 
((llm.api_key  llm.base_url  llm.name  llm.provider) 
  result = { 'provider': { llm.provider: {
      'npm': '@ai-sdk/anthropic' if llm.api_style = 'anthropic' else '@ai-sdk/openai-compatible',
      'options': { 'baseURL': llm.base_url, 'apiKey': '{env:LLM_API_KEY}' },
      'models': { llm.name: {} }
  } } })

---

## Code Evidence

Line 16: llm = settings.llm
Line 17: if not (llm.api_key and llm.base_url and llm.name and llm.provider):

---

## Trigger Condition

The code attempts to access attributes on a likely None value (settings.llm), raising an AttributeError instead of returning None as required when any of the required fields is not present. This violates the specification's requirement that no exceptions be raised and that the function return None when those fields are missing/falsy.

---

## How to trigger the bug

When `settings.llm` is `None` (e.g., when LLM configuration is not loaded), the function dereferences `None.api_key` on line 17, raising an `AttributeError` instead of returning `None`. The specification requires the function to return `None` and raise no exceptions when fields are missing.

### Inputs

| Parameter | Value |
|-----------|-------|
| `settings.llm` | `None` (LLM configuration not loaded) |

### Expected (spec-correct) Output

`None`

### Actual (buggy) Output

`AttributeError: 'NoneType' object has no attribute 'api_key'`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from unittest.mock import patch
import config
from src.opencode_trace import _opencode_provider_config

with patch.object(config.settings, "llm", None):
    _opencode_provider_config()
# actual (buggy) output: AttributeError: 'NoneType' object has no attribute 'api_key'
# expected (correct) output: None
```

---

## Probe Script

```python
import sys
import os

# Ensure repo root is on the path so config and src package resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch

try:
    import config
    from src.opencode_trace import _opencode_provider_config

    # Bug trigger: settings.llm is None, which means no LLM config is loaded.
    # Per spec, the function should return None when fields are missing/falsy
    # and must not raise exceptions. The buggy code dereferences None.api_key.
    with patch.object(config.settings, "llm", None):
        actual = _opencode_provider_config()
        # If we reach here, the function did NOT raise — that means the bug
        # is already fixed, or the trigger didn't take effect.
        expected = None
        passed = actual is not expected
        if passed:
            print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
        else:
            print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except AttributeError as e:
    # This is the bug: accessing .api_key on None raises AttributeError
    # instead of returning None as required by the spec.
    print(f"CONFIRMED — AttributeError: {e}")
    print(f"Expected: None (return None when fields are missing)")
    print(f"Actual: AttributeError('NoneType' object has no attribute 'api_key')")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — AttributeError: 'NoneType' object has no attribute 'api_key'
Expected: None (return None when fields are missing)
Actual: AttributeError('NoneType' object has no attribute 'api_key')
```
