def _required_string(value, key: str, source: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source}: missing non-empty string '{key}'")
    return _clean_label(value)
