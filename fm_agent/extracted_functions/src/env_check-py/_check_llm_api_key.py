# [SPEC]
# Unit: src/env_check.py
#
# _check_llm_api_key(config) -> tuple[bool, str | None]
#
# Pre-condition:
#   - config is an object with a LLM_API_KEY attribute.
#
# Post-condition:
#   - Returns (True, None) when the value of config.LLM_API_KEY is a non-empty
#     string that does not appear in a fixed, predefined collection of known
#     placeholder or sentinel values.
#   - Returns (False, error_message) when config.LLM_API_KEY is empty (falsy)
#     or matches an entry in the predefined collection of known placeholder
#     values. In this case error_message is a fixed, human-readable diagnostic
#     string.
#   - The function performs no I/O and has no side effects.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _check_llm_api_key(config):
    ok = bool(config.LLM_API_KEY and config.LLM_API_KEY not in (
        "", "YOUR_LLM_API_KEY",
        "sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    ))
    return ok, "LLM_API_KEY is not set in .env file" if not ok else None
