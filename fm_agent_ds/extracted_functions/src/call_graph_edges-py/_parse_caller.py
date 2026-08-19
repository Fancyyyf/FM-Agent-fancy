def _parse_caller(value, source: str) -> CallerSelector:
    if not isinstance(value, dict):
        raise ValueError(f"{source}: missing object 'caller'")

    fqn = _optional_string(value.get("fqn", ""), "caller.fqn", source)
    if fqn:
        fqn = normalize_fqn_label(fqn)
    callsite_names = _string_list(
        value.get("callsite_names", []), "caller.callsite_names", source
    )

    if not fqn and not callsite_names:
        raise ValueError(
            f"{source}: at least one of 'caller.fqn' or "
            "'caller.callsite_names' must be non-empty"
        )

    return CallerSelector(fqn=fqn, callsite_names=callsite_names)
