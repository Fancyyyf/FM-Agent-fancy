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
