def _callee_match_names(callee_fqn: str, aliases: Sequence[str]) -> List[str]:
    names = [callee_fqn, callee_fqn.split("::")[-1]]
    for alias in aliases:
        if not alias:
            continue
        names.append(alias)
        if "::" in alias:
            names.append(alias.rsplit("::", 1)[-1])
    return list(dict.fromkeys(names))
