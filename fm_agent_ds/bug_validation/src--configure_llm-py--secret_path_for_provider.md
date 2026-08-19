# Bug Report: secret_path_for_provider

**Source file:** `src/configure_llm.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a Path identifying a filesystem location within the platform-specific user configuration directory. The returned path is deterministically derived from config.provider_id: equal provider_id values always produce equal paths on the same platform, and distinct provider_id values produce distinct paths. The path's filename begins with the prefix 'fm-agent-opencode-api-key.' and ends with a 10-character lowercase hexadecimal suffix. The parent directory of the returned path exists.

---

### Actual Behavior

Returns a pathlib.Path object for a file named 'fm-agent-opencode-api-key.<safe_provider_id>.<digest>' located in the directory returned by _private_opencode_secret_dir(). The directory is guaranteed to exist after the call (created if absent). safe_provider_id is derived from config.provider_id by replacing any character not in [A-Za-z0-9._-] with '_', stripping leading and trailing characters in '._-', and defaulting to 'provider' if the result is empty. digest is the first 10 characters of the SHA256 hex digest of config.provider_id encoded as UTF8. Formal post-condition: let raw = config.provider_id, safe = (re.sub(r'[^A-Za-z0-9._-]+', '_', raw).strip('._-')) or 'provider', digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:10], directory = _private_opencode_secret_dir(); then the return value = directory / f'fm-agent-opencode-api-key.{safe}.{digest}' and directory.exists() is True.

---

## Code Evidence

Line 6: return _private_opencode_secret_dir() / (
Line 7:     f"fm-agent-opencode-api-key.{safe_provider_id}.{digest}"
Line 8: )

---

## Trigger Condition

Specification requires the returned Path to be within the platformspecific user configuration directory, but the code builds the path inside _private_opencode_secret_dir(), which is only defined as a directory for secret keys and is not guaranteed to be a subdirectory of (or identical to) the user configuration directory. For example, on a typical Linux system the user configuration directory is ~/.config, while _private_opencode_secret_dir() may return ~/.opencode/secrets, which is outside the required directory.

---

## How to trigger the bug

The function `secret_path_for_provider` delegates to `_private_opencode_secret_dir()`, which on Linux/macOS resolves to the XDG state directory (`$XDG_STATE_HOME` or `~/.local/state`) rather than the XDG config directory (`$XDG_CONFIG_HOME` or `~/.config`). The spec requires the path to be within the platform-specific **configuration** directory, but the code places it in the **state** directory. These are distinct locations per the XDG Base Directory specification.

### Inputs

| Parameter | Value |
|-----------|-------|
| `config.provider_id` | `test-provider-42` |
| `config.provider_name` | `TestProvider` |
| `config.api_style` | `openai` |
| `config.base_url` | `https://test.example.com/v1` |
| `config.model_id` | `test-model` |
| `config.api_key` | `sk-fake-key-123` |
| `config.backend` | `opencode` |

### Expected (spec-correct) Output

A path within the platform config directory, e.g. `~/.config/fm-agent/opencode/fm-agent-opencode-api-key.test-provider-42.2428fffd89` — or some other location under the user **configuration** directory.

### Actual (buggy) Output

`/home/fancy/.local/state/fm-agent/opencode/fm-agent-opencode-api-key.test-provider-42.2428fffd89`

This is under `~/.local/state/` which is the XDG **state** directory, not the XDG **config** directory.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.configure_llm import LLMConfigInput, secret_path_for_provider
from pathlib import Path

config = LLMConfigInput(
    provider_id="test-provider",
    provider_name="Test",
    api_style="openai",
    base_url="https://example.com/v1",
    model_id="test-model",
    api_key="sk-fake-key",
)
path = secret_path_for_provider(config)
# On Linux: path will be under ~/.local/state/, not ~/.config/
# actual (buggy) output: ~/.local/state/fm-agent/opencode/fm-agent-opencode-api-key.test-provider.<digest>
# expected (correct) output: a path within the platform config directory (~/.config/ on Linux)
```

---

## Probe Script

```python
"""Probe for bug: secret_path_for_provider returns a path inside the XDG state
directory instead of the XDG config directory.

Bug ID: src--configure_llm-py--secret_path_for_provider
"""

import os
import sys
from pathlib import Path

# Ensure the project root (parent of src/) is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.chdir(str(_REPO_ROOT))


def _platform_config_dir() -> Path:
    """Return the platform-specific user configuration directory."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata)
        return Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    else:
        # Linux / POSIX: $XDG_CONFIG_HOME or ~/.config
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config).expanduser().resolve()
        return Path.home() / ".config"


try:
    from src.configure_llm import LLMConfigInput, secret_path_for_provider

    # Build a minimal config with a well-known provider_id
    config = LLMConfigInput(
        provider_id="test-provider-42",
        provider_name="TestProvider",
        api_style="openai",
        base_url="https://test.example.com/v1",
        model_id="test-model",
        api_key="sk-fake-key-123",
        backend="opencode",
    )

    actual_path = secret_path_for_provider(config)
    config_dir = _platform_config_dir()

    # Check: is actual_path within the config directory?
    try:
        actual_path.relative_to(config_dir)
        within_config = True
    except ValueError:
        within_config = False

    if not within_config:
        print(
            f"CONFIRMED — secret_path_for_provider returns path outside the "
            f"platform config directory.\n"
            f"  Returned path : {actual_path}\n"
            f"  Config dir   : {config_dir}\n"
            f"  State dir    : {actual_path.parent.parent}\n"
            f"  The returned path is under the XDG_STATE_HOME / state directory, "
            f"not under the XDG_CONFIG_HOME / config directory as the spec requires."
        )
    else:
        print(
            f"NOT CONFIRMED — returned path is within the config directory.\n"
            f"  Returned path: {actual_path}\n"
            f"  Config dir  : {config_dir}"
        )

except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"ERROR: {e}")
```

### Probe Output

```
CONFIRMED — secret_path_for_provider returns path outside the platform config directory.
  Returned path : /home/fancy/.local/state/fm-agent/opencode/fm-agent-opencode-api-key.test-provider-42.2428fffd89
  Config dir   : /home/fancy/.config
  State dir    : /home/fancy/.local/state/fm-agent
  The returned path is under the XDG_STATE_HOME / state directory, not under the XDG_CONFIG_HOME / config directory as the spec requires.
```
