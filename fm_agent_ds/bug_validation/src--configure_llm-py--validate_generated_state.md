# Bug Report: validate_generated_state

**Source file:** `src/configure_llm-py/validate_generated_state.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Raises ConfigWizardError when updated_toml is not syntactically valid TOML, when merged_opencode is not JSON-serializable, when merged_opencode lacks a 'provider' key whose value is a dict containing an entry keyed by config.provider_id, when that provider entry is not a dict, when its 'npm' field does not equal the adapter name corresponding to config.api_style, when its 'options' field is missing, not a dict, or has an 'apiKey' value that does not equal the string '{file:<opencode_secret_path>}', when its 'models' field is missing, not a dict, or does not contain config.model_id, or when any field of config required for configuration is empty, missing, or malformed. Returns with no effect when all generated outputs pass their respective format and structural validation.

---

### Actual Behavior

After execution, exactly one of the following outcomes occurs:

1. A `ConfigWizardError` is raised because:
   - `validate_input(config)` failed (invalid provider configuration), or
   - the generated OpenCode configuration is missing the required provider `config.provider_id`, or
   - the provider entry is not a dict, or
   - the adapter (`npm`) does not match `adapter_for_api_style(config.api_style)`, or
   - the options dict is missing or does not contain `'apiKey'` equal to `'{{file:opencode_secret_path}}'`, or
   - the models dict is missing or does not contain `config.model_id`.

2. A `TypeError` or `ValueError` is raised from `json.dumps(merged_opencode)` because `merged_opencode` is not JSON-serializable.

3. A `tomllib.TOMLDecodeError` (or similar parsing exception) is raised from `tomllib.loads(updated_toml)` because `updated_toml` is not valid TOML.

4. An exception is propagated from `adapter_for_api_style(config.api_style)` if the API style is unrecognised, causing that call to raise.

5. The function returns `None` (normal termination). In this case all of the following hold:
   - `validate_input(config)` succeeded, implying `config` meets all `LLMConfigInput` validity constraints.
   - `json.dumps(merged_opencode)` succeeded, i.e., `merged_opencode` is JSON-serializable.
   - `tomllib.loads(updated_toml)` succeeded, i.e., `updated_toml` is valid TOML.
   - `merged_opencode.get('provider')` is a dict and `config.provider_id` is a key in it. Let `entry = merged_opencode['provider'][config.provider_id]`.
   - `entry` is a dict.
   - `entry.get('npm') == adapter_for_api_style(config.api_style)`.
   - `entry.get('options')` is a dict and `options.get('apiKey') == f'{{file:{opencode_secret_path}}}'`.
   - `entry.get('models')` is a dict and `config.model_id` is a key in it.

---

## Code Evidence

Line 9: json.dumps(merged_opencode) and Line 10: tomllib.loads(updated_toml)

---

## Trigger Condition

Specification requires raising ConfigWizardError when merged_opencode is not JSON-serializable or updated_toml is invalid TOML, but the code raises TypeError/ValueError or TOMLDecodeError respectively, not ConfigWizardError.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|---|---|
| `config` (LLMConfigInput) | `provider_id="test-provider"`, `provider_name="Test Provider"`, `api_style="openai"`, `base_url="https://example.com/api"`, `model_id="test-model"`, `api_key="test-key-12345"`, `backend="opencode"` |
| `merged_opencode` (Test 1) | `{"key": b"bytes_not_json_serializable"}` — contains a `bytes` object that is not JSON-serializable |
| `merged_opencode` (Test 2) | `{"provider": {"test-provider": {"npm": "@ai-sdk/openai-compatible", "options": {"apiKey": "{file:/tmp/.../secret}"}, "models": {"test-model": {}}}}}` — valid JSON |
| `updated_toml` (Test 1) | `"[llm]\nname = 'test'"` — valid TOML |
| `updated_toml` (Test 2) | `"this is not valid toml [[[ broken"` — invalid TOML |

### Expected (spec-correct) Output

`ConfigWizardError` should be raised in both cases: when `merged_opencode` is not JSON-serializable and when `updated_toml` is invalid TOML.

### Actual (buggy) Output

- **Test 1 (JSON non-serializable)**: `TypeError: Object of type bytes is not JSON serializable`
- **Test 2 (Invalid TOML)**: `tomllib.TOMLDecodeError: Expected '=' after a key in a key/value pair (at line 1, column 6)`

In both cases, the code raises the wrong exception type — `TypeError` instead of `ConfigWizardError` for JSON failures, and `tomllib.TOMLDecodeError` instead of `ConfigWizardError` for TOML failures.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
from pathlib import Path
sys.path.insert(0, "src")
from configure_llm import validate_generated_state, ConfigWizardError, LLMConfigInput

# Test 1: non-JSON-serializable merged_opencode
config = LLMConfigInput(
    provider_id="test-provider", provider_name="Test Provider",
    api_style="openai", base_url="https://example.com/api",
    model_id="test-model", api_key="test-key", backend="opencode",
)
validate_generated_state(
    config,
    merged_opencode={"key": b"bytes"},
    updated_toml="[llm]\nname = 'test'",
    opencode_secret_path=Path("/tmp/ignore"),
)
# actual (buggy) output: TypeError: Object of type bytes is not JSON serializable
# expected (correct) output: ConfigWizardError

# Test 2: invalid TOML
validate_generated_state(
    config,
    merged_opencode={"provider": {"test-provider": {"npm": "@ai-sdk/openai-compatible", "options": {"apiKey": "{file:/tmp/ignore}"}, "models": {"test-model": {}}}}},
    updated_toml="this is not valid toml [[[ broken",
    opencode_secret_path=Path("/tmp/ignore"),
)
# actual (buggy) output: tomllib.TOMLDecodeError: Expected '=' after a key...
# expected (correct) output: ConfigWizardError
```

---

## Probe Script

```python
import sys
import tempfile
from pathlib import Path

# Probe runs from repo root. Add src/ to sys.path for configure_llm imports.
_repo_root = Path(__file__).resolve().parents[2]
_src_dir = _repo_root / "src"
sys.path.insert(0, str(_src_dir))

from configure_llm import validate_generated_state, ConfigWizardError, LLMConfigInput

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

# All generated test state lives in a fresh temp directory.
_tmp = Path(tempfile.mkdtemp(prefix="probe_validate_generated_state_"))


def _make_valid_config() -> LLMConfigInput:
    return LLMConfigInput(
        provider_id="test-provider",
        provider_name="Test Provider",
        api_style="openai",
        base_url="https://example.com/api",
        model_id="test-model",
        api_key="test-key-12345",
        backend="opencode",
    )


def test_json_non_serializable():
    """merged_opencode containing bytes → json.dumps raises TypeError, not ConfigWizardError."""
    config = _make_valid_config()
    merged_opencode = {"key": b"bytes_not_json_serializable"}
    updated_toml = "[llm]\nname = 'test'"
    secret_path = _tmp / "secret"

    try:
        validate_generated_state(
            config, merged_opencode, updated_toml, opencode_secret_path=secret_path
        )
        return ("NOT_CONFIRMED", "No exception raised for non-JSON-serializable input")
    except ConfigWizardError as e:
        return ("NOT_CONFIRMED", f"ConfigWizardError raised (spec-correct): {e}")
    except (TypeError, ValueError) as e:
        return ("CONFIRMED", f"{type(e).__name__} raised instead of ConfigWizardError: {e}")
    except Exception as e:
        return ("CONFIRMED", f"{type(e).__name__} raised instead of ConfigWizardError: {e}")


def test_invalid_toml():
    """Invalid TOML string → tomllib.loads raises TOMLDecodeError, not ConfigWizardError."""
    config = _make_valid_config()
    secret_path = _tmp / "secret"
    merged_opencode = {
        "provider": {
            "test-provider": {
                "npm": "@ai-sdk/openai-compatible",
                "options": {"apiKey": f"{{file:{secret_path}}}"},
                "models": {"test-model": {}},
            }
        }
    }
    updated_toml = "this is not valid toml [[[ broken"

    try:
        validate_generated_state(
            config, merged_opencode, updated_toml, opencode_secret_path=secret_path
        )
        return ("NOT_CONFIRMED", "No exception raised for invalid TOML input")
    except ConfigWizardError as e:
        return ("NOT_CONFIRMED", f"ConfigWizardError raised (spec-correct): {e}")
    except tomllib.TOMLDecodeError as e:
        return ("CONFIRMED", f"TOMLDecodeError raised instead of ConfigWizardError: {e}")
    except Exception as e:
        return ("CONFIRMED", f"{type(e).__name__} raised instead of ConfigWizardError: {e}")


def main() -> None:
    verdicts = []
    outputs = []

    result1, msg1 = test_json_non_serializable()
    outputs.append(f"Test 1 (JSON serialization): {result1} - {msg1}")
    verdicts.append(result1)

    result2, msg2 = test_invalid_toml()
    outputs.append(f"Test 2 (TOML validation): {result2} - {msg2}")
    verdicts.append(result2)

    for line in outputs:
        print(line)

    if "CONFIRMED" in verdicts:
        print("CONFIRMED")
    else:
        print("NOT CONFIRMED")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
```

### Probe Output

```
Test 1 (JSON serialization): CONFIRMED - TypeError raised instead of ConfigWizardError: Object of type bytes is not JSON serializable
Test 2 (TOML validation): CONFIRMED - TOMLDecodeError raised instead of ConfigWizardError: Expected '=' after a key in a key/value pair (at line 1, column 6)
CONFIRMED
```
