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
