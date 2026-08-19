# Bug Report: parse_existing_opencode_config

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/parse_existing_opencode_config.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When text is non-empty and contains valid JSON after stripping JSONC comment syntax, returns a dict whose keys and values are the parsed top-level JSON object. When text is empty or whitespace-only, returns an empty dict. When text is non-empty but does not contain valid JSON (after stripping JSONC comment syntax), raises ConfigWizardError with a message indicating the config is invalid JSON.

---

### Actual Behavior

After execution, either a dictionary is returned or ConfigWizardError is raised. If text.strip() is empty, the function returns {}. Otherwise, let s = _strip_jsonc(text). If json.loads(s) raises json.JSONDecodeError, ConfigWizardError('Existing OpenCode config is invalid JSON/JSONC; refusing to overwrite it.') is raised. If json.loads(s) succeeds but the result is not an instance of dict, ConfigWizardError('Existing OpenCode config must be a JSON object at the top level.') is raised. If the result is a dict, that dict is returned. Formally: (text.strip() = ""  returns {})  (text.strip()  ""  s = _strip_jsonc(text)  ( (d  Dict: json.loads(s) = d)  returns d )  (json.loads(s) undefined  raises ConfigWizardError_{invalid})  (json.loads(s) = x  isinstance(x,dict)  raises ConfigWizardError_{top_level_object}) )

---

## Code Evidence

```
Line 10:     if not isinstance(loaded, dict):
Line 11:         raise ConfigWizardError(
Line 12:             "Existing OpenCode config must be a JSON object at the top level."
Line 13:         )
```

---

## Trigger Condition

Specification requires returning a dict for any non-empty text containing valid JSON after stripping, but for text='[]' the code raises ConfigWizardError because the parsed value is a list, not a dict.

---

## How to trigger the bug

Describe the concrete inputs used in the probe, what the buggy code returns, and what the specification requires.

### Inputs

| Parameter | Value |
|-----------|-------|
| text | `"[]"` |

### Expected (spec-correct) Output

`dict` — The specification states that when text is non-empty and contains valid JSON after stripping JSONC comment syntax, it "returns a dict whose keys and values are the parsed top-level JSON object." The text `"[]"` is non-empty and valid JSON, so the spec implies a dict (or the parsed result) should be returned.

### Actual (buggy) Output

`ConfigWizardError("Existing OpenCode config must be a JSON object at the top level.")` — The code checks `not isinstance(loaded, dict)` at line 10 and raises ConfigWizardError because `json.loads("[]")` returns a list, not a dict. The spec does not enumerate non-dict valid JSON as an error case.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.configure_llm import parse_existing_opencode_config

result = parse_existing_opencode_config("[]")
# actual (buggy) output: ConfigWizardError: Existing OpenCode config must be a JSON object at the top level.
# expected (correct) output: A dict (or the parsed JSON value) — the spec does not list non-dict valid JSON as an error condition.
```

---

## Probe Script

```python
import sys
sys.path.insert(0, '.')

try:
    from src.configure_llm import parse_existing_opencode_config, ConfigWizardError
except ImportError as e:
    print(f'ERROR: {e}')
    sys.exit(1)

actual = None
expected = None
passed = False

try:
    result = parse_existing_opencode_config("[]")
    actual = type(result).__name__
    expected = "dict"
    passed = actual != expected
    if passed:
        print(f"CONFIRMED — actual: returned {actual!r} | expected: {expected!r} (spec claimed it returns a dict)")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")
except ConfigWizardError as e:
    actual = f"ConfigWizardError: {e}"
    expected = "dict (spec says valid JSON should return a dict)"
    passed = True
    print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual: 'ConfigWizardError: Existing OpenCode config must be a JSON object at the top level.' | expected: 'dict (spec says valid JSON should return a dict)'
```
