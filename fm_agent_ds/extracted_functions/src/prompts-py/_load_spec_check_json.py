def _load_spec_check_json(response):
    """Load a single JSON object from a specification-check response.

    The shared parser handles direct, fenced, and prose-wrapped structured
    responses.  This adapter retains the spec-checker's object-only contract
    and its ``JSONDecodeError`` failure type.
    """
    text = response.strip() if isinstance(response, str) else ""
    try:
        data = _parse_json_response(response)
    except ValueError as exc:
        raise json.JSONDecodeError(str(exc), text, 0) from exc
    if not isinstance(data, dict):
        raise json.JSONDecodeError("spec-check response must contain a JSON object", text, 0)
    return data
