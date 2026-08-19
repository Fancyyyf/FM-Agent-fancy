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
