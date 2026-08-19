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
