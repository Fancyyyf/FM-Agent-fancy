# [SPEC]
# Unit: src/incremental_reasoner-py/_validate_spec_update.py
#
# _validate_spec_update(data) -> dict
#
# Pre-condition:
#   - data is a value supplied by the caller representing a candidate spec-update decision
#
# Post-condition:
#   - If data is not a dict, raises ValueError with message indicating the top-level value must be an object
#   - If data is a dict but lacks any of the required keys (spec_updated, new_spec, info_updated,
#     new_info, updated_callees), raises ValueError naming every missing key
#   - If spec_updated or info_updated is present but not a bool, raises ValueError
#     indicating both must be booleans
#   - If new_spec or new_info is not a str, raises ValueError indicating both must be strings
#   - If updated_callees is not a list, or if any element of updated_callees is not a str
#     or is an empty/whitespace-only string, raises ValueError indicating updated_callees
#     must be an array of non-empty strings
#   - If spec_updated is True and new_spec is empty or consists only of whitespace, raises
#     ValueError indicating new_spec must be non-empty when spec_updated is true
#   - If info_updated is True and new_info is empty or consists only of whitespace, raises
#     ValueError indicating new_info must be non-empty when info_updated is true
#   - If no ValueError is raised, returns a dict containing every required key with the
#     same boolean values as the input, every string value stripped of leading and trailing
#     whitespace, and every element of updated_callees individually stripped
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _validate_spec_update(data):
    """Validate a direct LLM decision about a function's [SPEC]/[INFO] blocks."""
    if not isinstance(data, dict):
        raise ValueError("spec-update JSON must be an object")
    required = ("spec_updated", "new_spec", "info_updated", "new_info", "updated_callees")
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError("spec-update JSON missing required field(s): " + ", ".join(missing))
    if not isinstance(data["spec_updated"], bool) or not isinstance(data["info_updated"], bool):
        raise ValueError("spec-update JSON fields spec_updated and info_updated must be booleans")
    if not isinstance(data["new_spec"], str) or not isinstance(data["new_info"], str):
        raise ValueError("spec-update JSON fields new_spec and new_info must be strings")
    if not isinstance(data["updated_callees"], list) or not all(
        isinstance(name, str) and name.strip() for name in data["updated_callees"]
    ):
        raise ValueError("spec-update JSON field updated_callees must be an array of non-empty strings")
    if data["spec_updated"] and not data["new_spec"].strip():
        raise ValueError("spec-update JSON requires non-empty new_spec when spec_updated is true")
    if data["info_updated"] and not data["new_info"].strip():
        raise ValueError("spec-update JSON requires non-empty new_info when info_updated is true")
    return {
        "spec_updated": data["spec_updated"],
        "new_spec": data["new_spec"].strip(),
        "info_updated": data["info_updated"],
        "new_info": data["new_info"].strip(),
        "updated_callees": [name.strip() for name in data["updated_callees"]],
    }
