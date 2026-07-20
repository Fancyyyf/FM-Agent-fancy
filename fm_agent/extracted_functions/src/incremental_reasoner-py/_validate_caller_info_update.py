# [SPEC]
# Unit: src/incremental_reasoner-py/_validate_caller_info_update.py
#
# _validate_caller_info_update(data) -> dict
#
# Pre-condition:
#   - `data` is a JSON-deserialized value from a direct LLM call that is expected to describe whether one caller's [INFO] block needs updating after a callee spec change
#
# Post-condition:
#   - Returns a dict with exactly two keys: "info_updated" (bool) and "new_info" (str, with leading and trailing whitespace stripped)
#   - When "info_updated" is True in the returned dict, "new_info" is guaranteed to be a non-empty string
#   - Raises ValueError if `data` is not a dict, if either required key ("info_updated", "new_info") is absent, if "info_updated" is not a boolean, if "new_info" is not a string, or if "info_updated" is True with an empty or whitespace-only "new_info"
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _validate_caller_info_update(data):
    """Validate a direct LLM decision about one caller's [INFO] block."""
    if not isinstance(data, dict):
        raise ValueError("caller-info JSON must be an object")
    required = ("info_updated", "new_info")
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError("caller-info JSON missing required field(s): " + ", ".join(missing))
    if not isinstance(data["info_updated"], bool):
        raise ValueError("caller-info JSON field info_updated must be a boolean")
    if not isinstance(data["new_info"], str):
        raise ValueError("caller-info JSON field new_info must be a string")
    if data["info_updated"] and not data["new_info"].strip():
        raise ValueError("caller-info JSON requires non-empty new_info when info_updated is true")
    return {"info_updated": data["info_updated"], "new_info": data["new_info"].strip()}
