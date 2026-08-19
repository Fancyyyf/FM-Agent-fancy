# Bug Report: validate_llm_setting

**Source file:** `src/configure_llm.py::validate_llm_setting`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Raises ConfigWizardError when key is not a recognized LLM configuration setting key. When key is recognized, raises ConfigWizardError when value fails the validation constraint associated with that key: a constraint requiring a non-empty trimmed string (value is empty or consists only of whitespace after stripping); a constraint requiring a syntactically valid absolute URL with http or https scheme (value does not satisfy it); a constraint requiring membership in a fixed set of recognized identifiers (value is absent from that set); or a constraint delegating to an API style adapter (the adapter rejects value). Returns with no effect when key is recognized and value satisfies all constraints associated with that key.

---

### Actual Behavior

The function validate_llm_setting(key, value) either returns None or raises an exception. If key is not in _LLM_TOML_KEYS, it raises ConfigWizardError("Unsupported LLM setting: {key}"). If key == 'provider' and value.strip() is empty, it raises ConfigWizardError("Provider ID must not be empty."). If key == 'base_url', it calls validate_base_url(value.strip()) which may raise an exception if value.strip() is not a syntactically valid absolute URL with http or https scheme; otherwise it does not raise. If key == 'backend' and value not in _BACKENDS, it raises ConfigWizardError with message listing supported backends. If key == 'api_style', it calls adapter_for_api_style(value) which may raise an exception if value is not a recognized API style; otherwise it does not raise. Otherwise, if none of the above conditions cause an exception, the function returns None without side effects.

---

## Code Evidence

Line 7:     if key == "base_url":
Line 8:         validate_base_url(value.strip())
Line 14:     elif key == "api_style":
Line 15:         adapter_for_api_style(value)

---

## Trigger Condition

For base_url and api_style, the specification requires raising ConfigWizardError when the value fails validation. However, the code delegates to validate_base_url and adapter_for_api_style, which may raise exceptions that are not ConfigWizardError (e.g., ValueError). Thus, the code's behavior does not conform to the required exception type.

---

## How to trigger the bug

The automatic analysis correctly identified spec-to-implementation gaps, although the exact mechanism differs from the trigger analysis. The `base_url` and `api_style` keys both correctly raise `ConfigWizardError` for invalid values — the delegated functions (`validate_base_url`, `adapter_for_api_style`) already raise `ConfigWizardError` and no other exception type is propagated. The actual bug is that the `"name"` and `"effort"` keys have **no validation at all**: the spec requires them to reject invalid values with `ConfigWizardError`, but the function returns `None` silently.

### Inputs

| Parameter | Value |
|-----------|-------|
| `key` | `"name"` |
| `value` | `""` (empty string) |

### Expected (spec-correct) Output

`ConfigWizardError` is raised (because `"name"` is a recognized key and its constraint requires a non-empty trimmed string).

### Actual (buggy) Output

`None` is returned — the function completes without raising any error, silently accepting the invalid empty value.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent")
from src.configure_llm import validate_llm_setting, ConfigWizardError

# Bug: empty 'name' value should raise ConfigWizardError but returns None
result = validate_llm_setting("name", "")
# actual (buggy) output: None (no exception raised)
# expected (correct) output: ConfigWizardError raised

# Also reproducible for 'effort':
validate_llm_setting("effort", "invalid")
# actual (buggy) output: None (no exception raised)
# expected (correct) output: ConfigWizardError raised
```

---

## Probe Script

```python
#!/usr/bin/env python3
"""Probe script for bug ID: src--configure_llm-py--validate_llm_setting.

Tests whether validate_llm_setting() correctly raises ConfigWizardError
for ALL recognized keys when given invalid values, as required by the spec.

Bug summary: The spec claims every recognized key is validated, but
'name' and 'effort' keys are not validated at all — they silently
accept empty/invalid values instead of raising ConfigWizardError.
"""
import sys
import os
import tempfile

# FM-Agent self-validation guard: use a temp directory as workspace
tmpdir = tempfile.mkdtemp(prefix="probe_validate_llm_setting_")
os.chdir(tmpdir)

sys.path.insert(0, "/home/fancy/Projects_Vault/FM-Agent")

try:
    from src.configure_llm import (
        validate_llm_setting,
        ConfigWizardError,
        _LLM_TOML_KEYS,
        _EFFORTS,
    )

    bugs: list[str] = []
    non_confirmed: list[str] = []

    # ------------------------------------------------------------------
    # Test 1: 'name' key — spec requires non-empty trimmed string
    # ------------------------------------------------------------------
    for val in ["", "   "]:
        try:
            result = validate_llm_setting("name", val)
            bugs.append(
                f"'name' key with {val!r}: returned {result!r} — "
                f"spec requires ConfigWizardError for empty/whitespace trimmed value"
            )
        except ConfigWizardError:
            non_confirmed.append(f"'name' key with {val!r}: correctly raised ConfigWizardError")
        except Exception as e:
            bugs.append(
                f"'name' key with {val!r}: raised {type(e).__name__}='{e}' — "
                f"spec requires ConfigWizardError"
            )

    # Valid name values should pass
    for val in ["my-model", "a"]:
        try:
            result = validate_llm_setting("name", val)
            if result is not None:
                bugs.append(f"'name' key with {val!r}: unexpected return {result!r}")
            else:
                non_confirmed.append(f"'name' key with {val!r}: correctly returned None")
        except Exception as e:
            bugs.append(
                f"'name' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"on valid input"
            )

    # ------------------------------------------------------------------
    # Test 2: 'effort' key — spec requires membership in fixed set
    # ------------------------------------------------------------------
    invalid_efforts = ["invalid", "x", "super_high", "unknown_effort"]
    for val in invalid_efforts:
        if val in _EFFORTS:
            continue  # should not happen but be safe
        try:
            result = validate_llm_setting("effort", val)
            bugs.append(
                f"'effort' key with {val!r}: returned {result!r} — "
                f"spec requires ConfigWizardError for value outside {_EFFORTS}"
            )
        except ConfigWizardError:
            non_confirmed.append(
                f"'effort' key with {val!r}: correctly raised ConfigWizardError"
            )
        except Exception as e:
            bugs.append(
                f"'effort' key with {val!r}: raised {type(e).__name__}='{e}' — "
                f"spec requires ConfigWizardError"
            )

    # Valid effort values should pass
    for val in _EFFORTS:
        try:
            result = validate_llm_setting("effort", val)
            if result is not None:
                bugs.append(f"'effort' key with {val!r}: unexpected return {result!r}")
            else:
                non_confirmed.append(f"'effort' key with {val!r}: correctly returned None")
        except Exception as e:
            bugs.append(
                f"'effort' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"on valid input"
            )

    # ------------------------------------------------------------------
    # Test 3: 'base_url' key — verify it DOES raise ConfigWizardError
    #         (trigger_condition claimed wrong exception, but code is fine)
    # ------------------------------------------------------------------
    invalid_urls = ["", "   ", "not-a-url", "ftp://example.com", "http:///"]
    for val in invalid_urls:
        try:
            validate_llm_setting("base_url", val)
            bugs.append(f"'base_url' key with {val!r}: returned without error")
        except ConfigWizardError:
            pass  # correct
        except Exception as e:
            bugs.append(
                f"'base_url' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"instead of ConfigWizardError"
            )

    # ------------------------------------------------------------------
    # Test 4: 'api_style' key — verify it DOES raise ConfigWizardError
    # ------------------------------------------------------------------
    for val in ["grok", "invalid"]:
        try:
            validate_llm_setting("api_style", val)
            bugs.append(f"'api_style' key with {val!r}: returned without error")
        except ConfigWizardError:
            pass  # correct
        except Exception as e:
            bugs.append(
                f"'api_style' key with {val!r}: raised {type(e).__name__}='{e}' "
                f"instead of ConfigWizardError"
            )

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    if bugs:
        print(f"CONFIRMED — found {len(bugs)} spec violation(s):")
        for b in bugs:
            print(f"  - {b}")
        print(
            f"(base_url and api_style correctly raise ConfigWizardError; "
            f"the bug is that 'name' and 'effort' keys have no validation "
            f"against their spec constraints)"
        )
    else:
        print("NOT CONFIRMED — all recognized keys validated correctly with ConfigWizardError")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — found 6 spec violation(s):
  - 'name' key with '': returned None — spec requires ConfigWizardError for empty/whitespace trimmed value
  - 'name' key with '   ': returned None — spec requires ConfigWizardError for empty/whitespace trimmed value
  - 'effort' key with 'invalid': returned None — spec requires ConfigWizardError for value outside ('', 'low', 'medium', 'high')
  - 'effort' key with 'x': returned None — spec requires ConfigWizardError for value outside ('', 'low', 'medium', 'high')
  - 'effort' key with 'super_high': returned None — spec requires ConfigWizardError for value outside ('', 'low', 'medium', 'high')
  - 'effort' key with 'unknown_effort': returned None — spec requires ConfigWizardError for value outside ('', 'low', 'medium', 'high')
(base_url and api_style correctly raise ConfigWizardError; the bug is that 'name' and 'effort' keys have no validation against their spec constraints)
```
