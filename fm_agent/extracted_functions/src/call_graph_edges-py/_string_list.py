def _string_list(value, key: str, source: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{source}: '{key}' must be a string array")
    out = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, str):
            raise ValueError(f"{source}: {key}[{idx}] must be a string")
        label = _clean_label(item)
        if label:
            out.append(label)
    return tuple(out)
