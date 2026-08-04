def _add_resolved_extra_edge(
    caller_fqn,
    edge: _ResolvedExtraEdge,
    phase_fqns,
    callees_map,
    callers_map,
    all_callees_map,
    edge_aliases_map,
):
    """Inject one resolved supplemental edge and attach its callee aliases."""
    callee_fqn = edge.callee_fqn
    if caller_fqn == callee_fqn:
        return False

    before = len(all_callees_map[caller_fqn])
    all_callees_map[caller_fqn].add(callee_fqn)
    edge_aliases_map[callee_fqn][caller_fqn].update(edge.info_names)

    if callee_fqn in phase_fqns:
        callees_map[caller_fqn].add(callee_fqn)
        callers_map[callee_fqn].add(caller_fqn)

    return len(all_callees_map[caller_fqn]) != before
