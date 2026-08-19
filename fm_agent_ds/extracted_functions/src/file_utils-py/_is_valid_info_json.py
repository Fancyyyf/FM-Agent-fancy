def _is_valid_info_json(data):
    """Check that .info.json contains exactly the supported fields."""
    if not isinstance(data, dict) or set(data) != {"callees"}:
        return False

    callees = data["callees"]
    if not isinstance(callees, list):
        return False

    for callee in callees:
        if not isinstance(callee, dict) or set(callee) != _CALLEE_FIELDS:
            return False
        if not all(isinstance(callee[field], str) for field in _CALLEE_FIELDS):
            return False

    return True
