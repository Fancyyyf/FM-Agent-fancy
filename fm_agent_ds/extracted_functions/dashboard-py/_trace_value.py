def _trace_value(d, *keys):
    """Read plain or opencode-trace delta-prefixed fields."""
    if not isinstance(d, dict):
        return None
    for key in keys:
        for candidate in (key, f"+{key}", f"*{key}"):
            if candidate in d:
                return d[candidate]
    return None
