def _is_valid_spec_json(data):
    """Check that .spec.json contains exactly the supported fields."""
    if not isinstance(data, dict):
        return False
    if set(data) != _SPEC_FIELDS:
        return False
    return all(isinstance(data[field], str) for field in _SPEC_FIELDS)
