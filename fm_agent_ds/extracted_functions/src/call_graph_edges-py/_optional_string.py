def _optional_string(value, key: str, source: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{source}: '{key}' must be a string")
    return _clean_label(value)
