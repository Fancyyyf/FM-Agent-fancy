def _parse_callee(value, source: str) -> CalleeTarget:
    if not isinstance(value, dict):
        raise ValueError(f"{source}: missing object 'callee'")

    fqn = _required_string(value.get("fqn"), "callee.fqn", source)
    info_names = _string_list(value.get("info_names", []), "callee.info_names", source)
    return CalleeTarget(fqn=fqn, info_names=info_names)
