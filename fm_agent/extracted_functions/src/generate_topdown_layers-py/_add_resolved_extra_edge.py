# [SPEC]
# Unit: src/generate_topdown_layers-py/_add_resolved_extra_edge.py
#
# _add_resolved_extra_edge(caller_fqn, edge, phase_fqns, callees_map, callers_map, all_callees_map, edge_aliases_map) -> bool
#
# Pre-condition:
#   - caller_fqn is a non-empty string (FQN of the calling function)
#   - edge is a _ResolvedExtraEdge with a callee_fqn attribute of type string and an info_names attribute that is an iterable of strings
#   - phase_fqns is a collection of FQN strings representing functions within the current phase
#   - callees_map, callers_map, and all_callees_map are mutable dicts mapping FQN strings to mutable sets of FQN strings
#   - edge_aliases_map is a mutable dict mapping callee FQNs to dicts of (caller FQN → mutable set of strings)
#   - all_callees_map[caller_fqn], edge_aliases_map[edge.callee_fqn], and edge_aliases_map[edge.callee_fqn][caller_fqn] are all initialized as mutable collections
#
# Post-condition:
#   - Returns True if and only if edge.callee_fqn was not a member of all_callees_map[caller_fqn] prior to the call
#   - Returns False without modifying any map when caller_fqn equals edge.callee_fqn (self-edge)
#   - After the call, edge.callee_fqn is a member of all_callees_map[caller_fqn]
#   - After the call, every string from edge.info_names is a member of edge_aliases_map[edge.callee_fqn][caller_fqn]
#   - If edge.callee_fqn is a member of phase_fqns, then edge.callee_fqn is added to callees_map[caller_fqn] and caller_fqn is added to callers_map[edge.callee_fqn]
#   - If edge.callee_fqn is not a member of phase_fqns, neither callees_map nor callers_map is modified
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
