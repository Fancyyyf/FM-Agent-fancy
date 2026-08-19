import sys
import os

# Use a temporary workspace for any runtime artifacts
tmpdir = os.environ.get("TMPDIR", "/tmp")
os.chdir("/home/fancy/Projects_Vault/FM-Agent")

sys.path.insert(0, "src")

try:
    from configure_llm import update_env_text

    # Input with two LLM_API_KEY lines — spec says exactly one should remain
    input_text = (
        "LLM_API_KEY=first-old-key\n"
        "LLM_API_KEY=second-old-key\n"
        "OTHER_VAR=keep_me\n"
    )
    api_key = "new-test-api-key"

    actual = update_env_text(input_text, api_key)

    occurrences = actual.count("LLM_API_KEY=")

    # Spec requires exactly one ENV_SECRET_KEY line in output
    expected_occurrences = 1

    # Bug reproduced if output has != 1 occurrences
    bug_reproduced = occurrences != expected_occurrences

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_reproduced:
    print(
        f"CONFIRMED — LLM_API_KEY= appears {occurrences} times (expected exactly 1). "
        f"Actual output:\n{actual!r}"
    )
else:
    print(
        f"NOT CONFIRMED — LLM_API_KEY= appears {occurrences} time(s), "
        f"which matches the expected count of {expected_occurrences}."
    )
