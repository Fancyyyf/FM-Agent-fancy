# [SPEC]
# Unit: src/llm_client.py
#
# _metadata_body() -> dict
#
# Pre-condition:
#   - None (takes no arguments)
#
# Post-condition:
#   - Returns a dictionary with exactly one top-level key "metadata", whose value is a nested dictionary containing a "user_id" key
#   - The value associated with "user_id" is a stable, consistent string that identifies the current environment across calls within the same installation
# [SPEC]

# [INFO]
# _stable_user_id() -> str
#   Pre-condition: None (takes no arguments)
#   Post-condition: Returns a non-empty string: the value of `settings.inject.id` when truthy, otherwise a predefined static default.
# [INFO]

def _metadata_body():
    return {"metadata": {"user_id": _stable_user_id()}}
