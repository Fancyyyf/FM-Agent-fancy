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
