def _validate_spec_update(data):
    """Validate a direct LLM decision about function metadata sidecars."""
    if not isinstance(data, dict):
        raise ValueError("spec-update JSON must be an object")
    required = ("spec_updated", "new_spec", "info_updated", "new_info", "updated_callees")
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError("spec-update JSON missing required field(s): " + ", ".join(missing))
    if not isinstance(data["spec_updated"], bool) or not isinstance(data["info_updated"], bool):
        raise ValueError("spec-update JSON fields spec_updated and info_updated must be booleans")
    if not isinstance(data["updated_callees"], list) or not all(
        isinstance(name, str) and name.strip() for name in data["updated_callees"]
    ):
        raise ValueError("spec-update JSON field updated_callees must be an array of non-empty strings")
    if data["spec_updated"]:
        if not isinstance(data["new_spec"], dict):
            raise ValueError("spec-update JSON requires object new_spec when spec_updated is true")
        if not _is_valid_spec_json(data["new_spec"]):
            raise ValueError("spec-update JSON new_spec must match the .spec.json schema")
    if data["info_updated"]:
        if not isinstance(data["new_info"], dict):
            raise ValueError("spec-update JSON requires object new_info when info_updated is true")
        if not _is_valid_info_json(data["new_info"]):
            raise ValueError("spec-update JSON new_info must match the .info.json schema")
    return {
        "spec_updated": data["spec_updated"],
        "new_spec": _normalize_spec_dict(data["new_spec"]) if data["spec_updated"] else None,
        "info_updated": data["info_updated"],
        "new_info": _normalize_info_dict(data["new_info"]) if data["info_updated"] else None,
        "updated_callees": [name.strip() for name in data["updated_callees"]],
    }
