# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _resolve_callee_fqns(caller_fqn, callee_names, callees_map, edge_aliases_map=None) -> set
#
# Pre-condition:
#   - caller_fqn is a non-empty string that exists as a key in callees_map.
#   - callee_names is an iterable of non-empty strings; each represents a callee name
#     (the final component of a callee FQN, derived from its [INFO] entry in a caller's spec).
#   - callees_map maps each caller FQN to an iterable of callee FQNs (strings of the form
#     "path::component::...::FunctionName").
#   - edge_aliases_map, when provided, maps callee_fqn -> {caller_fqn -> iterable of alias
#     strings}, providing alternative names for a callee as seen by a specific caller.
#
# Post-condition:
#   - Returns a (possibly empty) set of callee FQN strings.
#   - Every returned FQN belongs to callees_map[caller_fqn].
#   - A callee FQN is included if and only if its final "::"-separated component (the stem)
#     matches any string in callee_names, case-insensitively, OR any alias in
#     edge_aliases_map for that (callee FQN, caller_fqn) pair matches any string in
#     callee_names, case-insensitively.
#   - A callee FQN whose stem or alias matches more than one name in callee_names is
#     included exactly once (duplicate callee FQNs are not returned).
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _resolve_callee_fqns(caller_fqn, callee_names, callees_map, edge_aliases_map=None):
    """
    Map callee names reported by opencode (the [INFO] entries whose expected spec changed)
    back to the FQNs of caller_fqn's callees.

    A callee is identified in the [INFO] block by its name; this matches that name against
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
