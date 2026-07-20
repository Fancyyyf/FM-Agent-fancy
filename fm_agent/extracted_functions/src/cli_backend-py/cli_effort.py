# [SPEC]
# Unit: fm_agent/extracted_functions/src/cli_backend-py/cli_effort.py
#
# cli_effort() -> str
#
# Pre-condition:
#   - The LLM_EFFORT environment variable is either unset or contains a string
#
# Post-condition:
#   - Returns the value of the LLM_EFFORT environment variable with leading
#     and trailing whitespace removed
#   - Returns an empty string when LLM_EFFORT is not set or when its value
#     consists entirely of whitespace
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def cli_effort():
    return os.environ.get("LLM_EFFORT", "").strip()
