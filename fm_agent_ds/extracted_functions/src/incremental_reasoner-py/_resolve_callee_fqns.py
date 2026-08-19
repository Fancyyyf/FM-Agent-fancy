def _resolve_callee_fqns(caller_fqn, callee_names, callees_map, edge_aliases_map=None):
    """
    Map callee names reported by opencode (the .info.json entries whose expected spec changed)
    back to the FQNs of caller_fqn's callees.

    A callee is identified in .info.json by its name; this matches that name against
    the final component (stem) of each of caller_fqn's callee FQNs, case-insensitively, and
    returns every matching callee FQN (a name shared by callees in several files resolves to
    all of them).
    """
    wanted = {n.strip() for n in callee_names if n and n.strip()}
    wanted_lower = {n.lower() for n in wanted}
    resolved = set()
    for callee_fqn in callees_map.get(caller_fqn, ()):
        stem = callee_fqn.split("::")[-1]
        aliases = set()
        if edge_aliases_map:
            aliases.update(edge_aliases_map.get(callee_fqn, {}).get(caller_fqn, ()))
        alias_lower = {alias.lower() for alias in aliases}
        if stem in wanted or stem.lower() in wanted_lower or aliases & wanted or alias_lower & wanted_lower:
            resolved.add(callee_fqn)
    return resolved
