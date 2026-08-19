# Bug Report: _preview

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a human-readable multi-line string. The string contains the provider_id, provider_name, api_style, base_url, and model_id values from config on individually labeled lines. The api_key from config appears on a labeled line in a masked form that does not expose the full plaintext key. The string also lists, under a section header stating they will be updated, the filesystem paths of: paths.toml_path, paths.env_path, paths.opencode_config_path, and the provider-specific secret key file path determined from config.

---

### Actual Behavior

The function either returns a string or raises an exception. If it returns normally, the return value result satisfies: result == "FM-Agent LLM configuration\n\nProvider ID:   " + config.provider_id + "\nProvider name: " + config.provider_name + "\nAPI protocol:  " + config.api_style + "\nBase URL:      " + config.base_url + "\nModel ID:      " + config.model_id + "\nAPI key:       " + mask_secret(config.api_key) + "\n\nThe following files will be updated:\n  - " + paths.toml_path + "\n  - " + paths.env_path + "\n  - " + paths.opencode_config_path + "\n  - " + str(secret_path_for_provider(config)) + "\n". The objects config and paths are not mutated; their attributes retain the values they had at function entry. If an exception is raised by secret_path_for_provider or mask_secret (or any internal operation), the function terminates by propagating that exception; no return value is produced and config/paths remain unchanged.

---

## Code Evidence

Line 12:             f"API key:       {mask_secret(config.api_key)}"

---

## Trigger Condition

The specification expects _preview to always return a human-readable string, but with config.api_key empty, mask_secret('') violates its precondition and raises an exception, causing _preview to propagate that exception and not return a string.

---

## How to trigger the bug

The verification report claims that passing an empty API key (`config.api_key = ""`) causes `mask_secret('')` to raise an exception, which then propagates through `_preview`. However, inspection of the actual `mask_secret` implementation shows that it explicitly handles empty strings by returning `""`:

```python
def mask_secret(secret: str) -> str:
    if not secret:
        return ""
    ...
```

The probe confirms that `_preview` returns a valid string when called with an empty API key, with the "API key" line showing an empty value after the label. No exception is raised.

### Inputs

| Parameter | Value |
|-----------|-------|
| `config.api_key` | `""` (empty string) |
| `config.provider_id` | `"test-provider"` |
| `config.provider_name` | `"Test Provider"` |
| `config.api_style` | `"openai"` |
| `config.base_url` | `"https://api.example.com/v1"` |
| `config.model_id` | `"test-model"` |
| `config.backend` | `"opencode"` |

### Expected (spec-correct) Output

A string with `API key:       ` (empty masked value after the label).

### Actual (buggy) Output

A string with `API key:       ` (empty masked value after the label) — matches the spec-expected behavior. No exception is raised.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.configure_llm import _preview, LLMConfigInput, WizardPaths
from pathlib import Path
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    p = Path(tmpdir)
    config = LLMConfigInput(
        provider_id="test", provider_name="Test",
        api_style="openai", base_url="https://api.example.com/v1",
        model_id="test-model", api_key="", backend="opencode",
    )
    paths = WizardPaths(p, p/".env", p/"fm-agent.toml", p/"opencode.json")
    result = _preview(config, paths)
    print(result)
# actual (buggy) output: a valid multi-line string — no exception raised
# expected (correct) output: a valid multi-line string
```

---

## Probe Script

```python
"""Probe script for bug src--configure_llm-py--_preview.

The verification claims _preview raises an exception when config.api_key is
empty, because mask_secret('') allegedly violates its precondition and raises.
The spec requires _preview to always return a human-readable string.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add repo root to sys.path so the src package is importable.
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

try:
    from src.configure_llm import _preview, LLMConfigInput, WizardPaths
except Exception as exc:
    print(f'ERROR: could not import src.configure_llm: {exc}')
    sys.exit(1)

_attempts_remaining = 3
_confirmed = False
_last_stdout = ""

for attempt in range(1, _attempts_remaining + 1):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            env_path = project_root / ".env"
            toml_path = project_root / "fm-agent.toml"
            opencode_config_path = project_root / "opencode.json"

            # Create valid paths in the temp directory
            toml_path.write_text('[llm]\nname = "test"\n', encoding="utf-8")
            env_path.write_text("", encoding="utf-8")
            opencode_config_path.write_text("{}", encoding="utf-8")

            config = LLMConfigInput(
                provider_id="test-provider",
                provider_name="Test Provider",
                api_style="openai",
                base_url="https://api.example.com/v1",
                model_id="test-model",
                api_key="",       # ← empty API key — the trigger condition
                backend="opencode",
            )
            paths = WizardPaths(
                project_root=project_root,
                env_path=env_path,
                toml_path=toml_path,
                opencode_config_path=opencode_config_path,
            )

            # Attempt 1: empty api_key with valid provider_id
            # Attempts 2-3: try with empty provider_id too (explore edge cases)
            if attempt == 2:
                config = LLMConfigInput(
                    provider_id="",
                    provider_name="Test Provider",
                    api_style="openai",
                    base_url="https://api.example.com/v1",
                    model_id="test-model",
                    api_key="",
                    backend="opencode",
                )
            elif attempt == 3:
                config = LLMConfigInput(
                    provider_id="",
                    provider_name="",
                    api_style="openai",
                    base_url="https://api.example.com/v1",
                    model_id="",
                    api_key="",
                    backend="opencode",
                )

            result = _preview(config, paths)
            # If we reach here, _preview returned normally (a string).
            is_string = isinstance(result, str)
            if is_string:
                _last_stdout = (
                    f"NOT CONFIRMED — _preview() returned a string "
                    f"instead of raising: {result!r}"
                )
            else:
                _last_stdout = (
                    f"CONFIRMED — _preview() returned non-string "
                    f"{type(result).__name__}: {result!r}"
                )
            print(_last_stdout)
            _confirmed = not is_string
            break

    except Exception as exc:
        # An exception was raised — this matches the claimed buggy behavior.
        _last_stdout = (
            f"CONFIRMED — _preview() raised {type(exc).__name__}: {exc}"
        )
        print(_last_stdout)
        _confirmed = True
        break

if not _confirmed:
    # Last attempt didn't confirm.
    if _last_stdout:
        pass  # already printed
    else:
        print("NOT CONFIRMED — all attempts exhausted, could not trigger the bug")
```

### Probe Output

```
NOT CONFIRMED — _preview() returned a string instead of raising: 'FM-Agent LLM configuration\n\nProvider ID:   test-provider\nProvider name: Test Provider\nAPI protocol:  openai\nBase URL:      https://api.example.com/v1\nModel ID:      test-model\nAPI key:       \n\nThe following files will be updated:\n  - /tmp/tmphx9kgl9f/fm-agent.toml\n  - /tmp/tmphx9kgl9f/.env\n  - /tmp/tmphx9kgl9f/opencode.json\n  - /home/fancy/.local/state/fm-agent/opencode/fm-agent-opencode-api-key.test-provider.793b2b6e7c'
```
