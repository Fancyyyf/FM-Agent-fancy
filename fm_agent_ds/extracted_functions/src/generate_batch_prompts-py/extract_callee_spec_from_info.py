def extract_callee_spec_from_info(
    info_dict: dict,
    callee_fqn: str,
    aliases: Optional[Sequence[str]] = None,
) -> Optional[dict]:
    """Return the callee object matching the requested FQN or edge aliases."""
    names = _callee_match_names(callee_fqn, aliases or ())
    callees = info_dict.get("callees", [])
    if not isinstance(callees, list):
        return None

    for callee in callees:
        if not isinstance(callee, dict):
            continue
        name = callee.get("name", "")
        if not isinstance(name, str):
            continue
        if any(_info_line_mentions_name(name, candidate) for candidate in names):
            return callee
    return None
