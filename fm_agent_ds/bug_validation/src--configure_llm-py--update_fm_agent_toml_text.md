# Bug Report: update_fm_agent_toml_text

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/configure_llm-py/update_fm_agent_toml_text.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns TOML content where, under the [llm] section, the name field is set to config.model_id, the provider field to config.provider_id, the base_url field to config.base_url, the backend field to config.backend, and the api_style field to config.api_style. Every other TOML section, every field outside [llm], and every comment is preserved unchanged.

---

### Actual Behavior

The function returns a string representing valid TOML content. In the returned TOML, the [llm] section contains the following updated fields: 'name' set to config.model_id, 'provider' set to config.provider_id, 'base_url' set to config.base_url, 'backend' set to config.backend, and 'api_style' set to config.api_style. All other sections, fields, and comments, including any other fields under [llm] not specified, remain exactly as in the input text. The function has no side effects. Formally: let result = update_fm_agent_toml_text(text, config); then result is a string such that parseTOML(result) is defined, and for each key k in {'name','provider','base_url','backend','api_style'}, the value of parseTOML(result)['llm'][k] equals getattr(config, k), and for any TOML element e (including sections, keys, comments) not in the set of updated [llm] keys, e is identical between parseTOML(result) and parseTOML(text).

---

## Code Evidence

Lines 2-11: return update_llm_settings_toml_text(text, {"name": config.model_id, "provider": config.provider_id, "base_url": config.base_url, "backend": config.backend, "api_style": config.api_style,})

---

## Trigger Condition

The specification requires that the output TOML contains an [llm] section with the specified fields set, which implies it must work even if the input lacks an [llm] section. However, update_llm_settings_toml_text has a pre-condition that text already contains an [llm] section. For the given counterexample text, the inner function will fail (e.g., raise KeyError or produce invalid output), so the code does not satisfy the specification.

---

## How to trigger the bug

The trigger condition claims that `update_llm_settings_toml_text` has a pre-condition requiring an existing `[llm]` section and will fail when the input lacks one. However, inspection of the source code at lines 427–434 of `src/configure_llm.py` shows an explicit `elif not llm_found:` branch that appends a new `[llm]` section and all target fields when no existing `[llm]` was found. The probe confirms this branch is reached and the function behaves as the specification requires.

### Inputs

| Parameter | Value |
|---|---|
| `text` | `# This is a comment\n[database]\nhost = "localhost"\nport = 5432\n` |
| `config.provider_id` | `"openrouter"` |
| `config.model_id` | `"test-model-123"` |
| `config.base_url` | `"https://api.test.example/v1"` |
| `config.backend` | `"opencode"` |
| `config.api_style` | `"openai"` |

### Expected (spec-correct) Output

`TOML string with [llm] section containing name="test-model-123", provider="openrouter", base_url="https://api.test.example/v1", backend="opencode", api_style="openai", preserving all other sections/comments from the input.`

### Actual (buggy) Output

`TOML string with [llm] section correctly containing all specified fields, plus the original [database] section and comment preserved unchanged. The output is valid TOML and parseable.`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys; sys.path.insert(0, '.')
from src.configure_llm import update_fm_agent_toml_text, LLMConfigInput

text = """# This is a comment
[database]
host = "localhost"
port = 5432
"""
config = LLMConfigInput(
    provider_id="openrouter",
    provider_name="OpenRouter",
    api_style="openai",
    base_url="https://api.test.example/v1",
    model_id="test-model-123",
    api_key="sk-test-key",
    backend="opencode",
)
result = update_fm_agent_toml_text(text, config)
print(result)
# actual (buggy) output: TOML with correct [llm] added — bug is NOT CONFIRMED
# expected (correct) output: TOML with correct [llm] added
```

---

## Probe Script

```python
import sys
import os

# Probe runs from repo root; ensure the root is on path.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _repo_root)

from src.configure_llm import update_fm_agent_toml_text, LLMConfigInput

# ---------------------------------------------------------------------------
# Trigger condition (verbatim from the bug report):
#   "The specification requires that the output TOML contains an [llm] section
#    with the specified fields set, which implies it must work even if the
#    input lacks an [llm] section. However, update_llm_settings_toml_text has
#    a pre-condition that text already contains an [llm] section. For the
#    given counterexample text, the inner function will fail (e.g., raise
#    KeyError or produce invalid output), so the code does not satisfy the
#    specification."
#
# --> Test: pass TOML text with NO [llm] section and verify the output.
# ---------------------------------------------------------------------------

# TOML text that deliberately has no [llm] section.
text_without_llm = """\
# This is a comment
[database]
host = "localhost"
port = 5432
"""

config = LLMConfigInput(
    provider_id="openrouter",
    provider_name="OpenRouter",
    api_style="openai",
    base_url="https://api.test.example/v1",
    model_id="test-model-123",
    api_key="sk-test-key",
    backend="opencode",
)

passed = False
actual = None

try:
    actual = update_fm_agent_toml_text(text_without_llm, config)

    import tomllib

    parsed = tomllib.loads(actual)

    # The specification requires that [llm] exists with the correct fields.
    # The trigger condition claims this will FAIL when there's no input [llm].
    # If the function DOES produce a valid [llm] section, the bug is NOT CONFIRMED.

    llm_section = parsed.get("llm")
    if llm_section is not None:
        # Check that the expected keys exist
        expected_keys = {"name", "provider", "base_url", "backend", "api_style"}
        actual_keys = set(llm_section.keys())
        if expected_keys.issubset(actual_keys):
            # Function works correctly – bug is NOT CONFIRMED.
            passed = False  # NOT confirmed
        else:
            passed = True  # CONFIRMED – missing keys
    else:
        passed = True  # CONFIRMED – no [llm] section at all

except Exception as exc:
    # The trigger condition claims this path is the bug
    passed = True  # CONFIRMED – function failed as claimed

if passed:
    print(f"CONFIRMED — bug reproduced: input without [llm] caused failure or invalid output. "
          f"Actual: {actual!r}")
else:
    print(f"NOT CONFIRMED — function successfully added [llm] section even without one in input. "
          f"Output TOML keys under [llm]: {list(parsed['llm'].keys())}")
```

### Probe Output

```
NOT CONFIRMED — function successfully added [llm] section even without one in input. Output TOML keys under [llm]: ['name', 'provider', 'base_url', 'backend', 'api_style']
```
