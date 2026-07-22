# [SPEC]
# Unit: fm_agent/extracted_functions/src/cli_backend-py/cli_effort.py
#
# cli_effort() -> str
#
# Pre-condition:
#   - `settings.llm.effort` is a string
#
# Post-condition:
#   - Returns the value of `settings.llm.effort` with leading and trailing
#     whitespace removed
#   - If the value is empty or consists only of whitespace, returns an empty
#     string
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def cli_effort():
    return settings.llm.effort.strip()
