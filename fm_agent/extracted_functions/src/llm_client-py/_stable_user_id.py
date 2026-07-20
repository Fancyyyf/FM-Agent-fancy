# [SPEC]
# Unit: src/llm_client.py
#
# _stable_user_id() -> str
#
# Pre-condition:
#   - None (takes no arguments)
#
# Post-condition:
#   - Returns the value of the INJECT_ID environment variable when that variable is set and its value is non-empty
#   - Returns a predefined static default value when INJECT_ID is not set or its value is empty
#   - The returned string is non-empty in all cases
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _stable_user_id():
    return os.environ.get("INJECT_ID") or _DEFAULT_INJECT_USER_ID
