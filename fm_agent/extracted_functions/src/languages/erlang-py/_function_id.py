def _function_id(uri: str, label: str) -> str:
    try:
        name, arity = label.rsplit("/", 1)
        int(arity)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"ELP function label has no valid arity: {label!r}") from exc
    if ":" in name and not name.startswith("'"):
        name = name.rsplit(":", 1)[1]
    module = _module_from_uri(uri)
    return f"{_escape_component(module)}__{_escape_component(name)}__{arity}"
