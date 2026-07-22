# [SPEC]
# Unit: src/llm_client.py
#
# _stable_user_id() -> str
#
# Pre-condition:
#   - None (takes no arguments)
#
# Post-condition:
#   - Returns the value of `settings.inject.id` when that value is truthy
#   - Returns the predefined static default `_DEFAULT_INJECT_USER_ID` when `settings.inject.id` is falsy (empty or None)
#   - The returned string is non-empty in all cases
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _stable_user_id():
    return settings.inject.id or _DEFAULT_INJECT_USER_ID
