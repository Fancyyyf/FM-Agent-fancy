# [SPEC]
# Unit: src/incremental_reasoner-py/_validate_module_selection.py
#
# _validate_module_selection(data) -> list[dict]
#
# Pre-condition:
#   - `data` is a JSON-deserialized value from a direct LLM call that is expected to select relevant modules for the incremental scope pass
#
# Post-condition:
#   - Returns a list of dicts, each containing exactly two keys: "phase" (int that is not a bool subtype) and "name" (non-empty str with leading and trailing whitespace stripped)
#   - Raises ValueError if `data` is not a list, if any element is not a dict, if the "phase" field is missing/not-an-int/is-a-bool for any element, or if the "name" field is missing/not-a-string/is-empty-or-whitespace-only for any element
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _validate_module_selection(data):
    """Validate the direct LLM response used to select relevant modules."""
    if not isinstance(data, list):
        raise ValueError("module-selection JSON must be an array")
    validated = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"module-selection item {index} must be an object")
        phase = item.get("phase")
        name = item.get("name")
        if isinstance(phase, bool) or not isinstance(phase, int):
            raise ValueError(f"module-selection item {index} requires integer field: phase")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"module-selection item {index} requires non-empty string field: name")
        validated.append({"phase": phase, "name": name.strip()})
    return validated
