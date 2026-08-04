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
