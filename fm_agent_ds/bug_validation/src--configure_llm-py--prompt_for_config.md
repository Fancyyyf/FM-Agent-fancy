# Bug Report: prompt_for_config

**Source file:** `src/configure_llm.py` (extracted from `fm_agent/extracted_functions/src/configure_llm-py/prompt_for_config.py`)
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a tuple of (config, validate_flag) where config is an LLMConfigInput instance with all fields populated from user terminal input: provider_id, provider_name, base_url, model_id, and api_key are non-empty strings; api_style is a member of the ApiStyle enumeration; and backend is 'opencode'. validate_flag is True when the user elected to validate the generated configuration, False otherwise. Configuration fields are collected interactively via stdout and stdin, with each field offering a default value that is accepted when the user provides empty input. Raises ConfigWizardError when the user's API style selection does not correspond to any recognized valid option. Re-prompts the user for any field whose input fails that field's validation rules, continuing until valid input is provided.

---

### Actual Behavior

If the user selects protocol '1' or '2', the function returns a tuple (config, validate) where config is an LLMConfigInput instance with: provider_id, provider_name, base_url, and model_id as non-empty strings (provider_name defaults to provider_id.title() when user provides empty input); api_style equal to 'openai' if selected = '1', else 'anthropic' if selected = '2'; base_url defaulting to 'https://openrouter.ai/api/v1' if api_style is 'openai' else 'https://api.anthropic.com/v1'; api_key a (possibly empty) string; and validate a boolean defaulting to True. If selected is not '1' or '2', a ConfigWizardError is raised and no value is returned. Formally: (selected  ('1','2')  ( config, validate: function returns (config, validate)  config.provider_id  ""  config.provider_name  ""  config.base_url  ""  config.model_id  ""  (selected = '1'  config.api_style = 'openai')  (selected = '2'  config.api_style = 'anthropic')  config.api_style = 'openai'  default_base = 'https://openrouter.ai/api/v1'  config.api_style = 'anthropic'  default_base = 'https://api.anthropic.com/v1'  validate  {True, False}))  (selected  ('1','2')  ConfigWizardError is raised).

---

## Code Evidence

Line 23: api_key = getpass("API key: ").strip() ; Line 25-32: config = LLMConfigInput(...) (does not set backend)

---

## Trigger Condition

The specification requires api_key to be a non-empty string, but the code accepts an empty API key (no re-prompting, getpass returns empty if user presses Enter). The specification also requires the config to have backend='opencode', which is never set by the code. Additionally, api_style is set to a plain string instead of an ApiStyle enumeration member as required.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| provider_id | `test-provider` |
| provider_name | `Test Provider` |
| API protocol | `1` (OpenAI-compatible) |
| API base URL | `https://custom.example.com/v1` |
| model_id | `gpt-4` |
| api_key | `<empty>` (user presses Enter without typing) |
| validate | No |

### Expected (spec-correct) Output

The function should re-prompt the user for a non-empty API key until valid input is provided. The returned `LLMConfigInput` must have a non-empty `api_key` string.

### Actual (buggy) Output

The function returns an `LLMConfigInput` with `api_key=''` (empty string) without any validation or re-prompting.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from configure_llm import prompt_for_config
import unittest.mock

_inputs = iter(["test-provider", "Test Provider", "1", "https://custom.example.com/v1", "gpt-4", "n"])

with unittest.mock.patch("builtins.input", lambda _: next(_inputs, "")):
    with unittest.mock.patch("configure_llm.getpass", lambda _: ""):
        config, validate = prompt_for_config()
        # actual (buggy) output: config.api_key == ''
        # expected (correct) output: config.api_key is a non-empty string
        assert config.api_key == '', "Expected empty api_key to confirm the bug"
```

---

## Probe Script

```py
import sys
import tempfile
import unittest.mock
from pathlib import Path

# Create a fresh temp directory for the probe workspace (self-validation guard)
_probe_tmp = Path(tempfile.mkdtemp(prefix="probe_prompt_for_config_"))

# Add src/ to sys.path so we can import configure_llm as the public entry point
# The probe is at fm_agent/bug_validation/probe_*.py — repo root is 3 levels up
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root / "src"))

try:
    from configure_llm import prompt_for_config, LLMConfigInput, ConfigWizardError

    # Simulate realistic user inputs for the interactive prompts.
    # Order matches the sequence in prompt_for_config:
    #   1. Provider ID     (_prompt with default "openrouter")
    #   2. Provider name   (_prompt with default provider_id.title())
    #   3. API protocol    (_prompt with default "1")
    #   4. API base URL    (_prompt with default based on protocol)
    #   5. Model ID        (_prompt, no default)
    #   6. Validate?       (_prompt_yes_no, default True)
    _inputs = iter(
        [
            "test-provider",  # provider_id
            "Test Provider",  # provider_name
            "1",              # API protocol: OpenAI
            "https://custom.example.com/v1",  # base_url (explicit to avoid confusion)
            "gpt-4",          # model_id
            "n",              # validate = False
        ]
    )

    def _fake_input(_prompt_text: str) -> str:
        try:
            return next(_inputs)
        except StopIteration:
            return ""

    def _fake_getpass(_prompt_text: str) -> str:
        # Return empty — this is the trigger condition for the bug
        return ""

    with unittest.mock.patch("builtins.input", _fake_input):
        with unittest.mock.patch("configure_llm.getpass", _fake_getpass):
            config, validate = prompt_for_config()

    # Check assertion: spec says api_key must be non-empty, code accepts empty
    if config.api_key == "":
        print(
            "CONFIRMED — empty API key accepted without re-prompting. "
            f"api_key={config.api_key!r}, backend={config.backend!r}, "
            f"api_style={config.api_style!r}"
        )
    else:
        print(
            f"NOT CONFIRMED — API key is non-empty: api_key={config.api_key!r}"
        )

except Exception as exc:
    print(f"ERROR: {exc}")
    sys.exit(1)
```

### Probe Output

```
API protocol:
  1. OpenAI-compatible
  2. Anthropic-compatible
CONFIRMED — empty API key accepted without re-prompting. api_key='', backend='opencode', api_style='openai'
```

---

## Additional Notes

- **backend='opencode'**: The `LLMConfigInput` dataclass has `backend: str = "opencode"` as a default value (line 71 of `src/configure_llm.py`), so even though the constructor call does not explicitly pass `backend`, the resulting config does have `backend='opencode'`. This claim does not manifest as a runtime bug — the default handles it.
- **api_style as enumeration**: `ApiStyle = Literal["openai", "anthropic"]` is a `typing.Literal` type alias, not an `enum.Enum`. The runtime values `"openai"` and `"anthropic"` are plain strings — there is no enumeration object to instantiate. This is a type-level spec mismatch, not a behavioral bug. All downstream code (`adapter_for_api_style`, string comparisons) works correctly with the string values.
