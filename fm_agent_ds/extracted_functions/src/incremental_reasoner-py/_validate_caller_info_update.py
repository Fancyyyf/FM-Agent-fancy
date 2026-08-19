def _validate_caller_info_update(data):
    """Validate a direct LLM decision about one caller's info sidecar."""
    if not isinstance(data, dict):
        raise ValueError("caller-info JSON must be an object")
    required = ("info_updated", "new_info")
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError("caller-info JSON missing required field(s): " + ", ".join(missing))
    if not isinstance(data["info_updated"], bool):
        raise ValueError("caller-info JSON field info_updated must be a boolean")
    if data["info_updated"]:
        if not isinstance(data["new_info"], dict):
            raise ValueError("caller-info JSON requires object new_info when info_updated is true")
        if not _is_valid_info_json(data["new_info"]):
            raise ValueError("caller-info JSON new_info must match the .info.json schema")
    return {
        "info_updated": data["info_updated"],
        "new_info": _normalize_info_dict(data["new_info"]) if data["info_updated"] else None,
    }
