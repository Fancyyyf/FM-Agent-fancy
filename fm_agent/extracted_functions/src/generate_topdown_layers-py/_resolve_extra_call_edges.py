# [SPEC]
# Unit: src/generate_topdown_layers-py/_resolve_extra_call_edges.py
#
# _resolve_extra_call_edges(extra_call_edges, phase_fqns, known_fqns) -> tuple[dict, dict]
#
# Pre-condition:
#   - extra_call_edges is None or an iterable of CallEdge objects, each carrying
#     a caller (with optional fqn string and callsite_names iterable of strings)
#     and a callee (with fqn string and optional info_names iterable of strings)
#   - phase_fqns is an iterable of FQN strings belonging to the current phase
#   - known_fqns is an iterable of all FQN strings across all phases
#
# Post-condition:
#   - Returns (by_caller_fqn, by_callsite): two dict-like mappings that return
#     an empty list for any key not explicitly present
#   - by_caller_fqn: maps each caller FQN (from edge.caller.fqn) to a list of
#     resolved-edge objects; a caller FQN appears as a key iff it is a member of
#     phase_fqns AND at least one supplied edge whose callee.fqn is a member of
#     known_fqns carries that exact caller FQN
#   - by_callsite: maps each callsite name string to a list of resolved-edge
#     objects; a callsite name appears as a key iff it is a valid source-code
#     identifier (begins with an ASCII letter or underscore, followed by zero or
#     more ASCII alphanumeric characters or underscores) AND at least one supplied
#     edge whose callee.fqn is a member of known_fqns lists that callsite in
#     edge.caller.callsite_names
#   - A single supplied edge can produce entries in both by_caller_fqn (via its
#     caller.fqn) and by_callsite (via each of its caller.callsite_names),
#     independently
#   - When extra_call_edges is None or empty, both returned mappings contain no
#     entries
#   - An edge whose callee.fqn is NOT a member of known_fqns produces NO entries
#     in either returned mapping (the edge is silently excluded)
#   - A caller FQN from edge.caller.fqn that is NOT a member of phase_fqns
#     produces NO entry in by_caller_fqn for that edge (the edge is silently
#     excluded with respect to that caller FQN, but may still produce entries in
#     by_callsite)
#   - Each resolved-edge object in the returned lists carries at minimum: the
#     callee FQN, a tuple of supplemental info names from the original edge's
#     callee.info_names, and a source identifier
# [SPEC]

# [INFO]
# re.fullmatch(pattern, string) -> Optional[Match]
#   Pre-condition: pattern is a compiled regex pattern or a string to be compiled;
#     string is the text to match against
#   Post-condition: returns a match object if the entire string matches the
#     pattern; returns None if the string does not fully match the pattern or if
#     the pattern is invalid
# [INFO]

def _resolve_extra_call_edges(extra_call_edges, phase_fqns, known_fqns):
    """Resolve supplemental edges into phase-local caller indexes."""
    by_caller_fqn = defaultdict(list)
    by_callsite = defaultdict(list)
    if not extra_call_edges:
        return by_caller_fqn, by_callsite

    phase_fqns = set(phase_fqns)
    known_fqns = set(known_fqns)
    for edge in extra_call_edges:
        callee_fqn = edge.callee.fqn
        if callee_fqn not in known_fqns:
            logging.warning(
                "Skipping supplemental edge from %s: callee.fqn %r "
                "was not found among extracted functions.",
                edge.source or "edge file",
                callee_fqn,
            )
            continue

        resolved = _ResolvedExtraEdge(
            callee_fqn=callee_fqn,
            info_names=tuple(edge.callee.info_names),
            source=edge.source,
        )

        if edge.caller.fqn:
            caller_fqn = edge.caller.fqn
            if caller_fqn in phase_fqns:
                by_caller_fqn[caller_fqn].append(resolved)
            else:
                logging.debug(
                    "Skipping supplemental edge from %s in current phase: "
                    "caller FQN %r is not in phase.",
                    edge.source or "edge file",
                    caller_fqn,
                )

        for callsite in edge.caller.callsite_names:
            if not re.fullmatch(r"[A-Za-z_]\w*", callsite):
                logging.warning(
                    "Skipping supplemental edge callsite selector %r from %s: "
                    "the current scanner only matches identifier callsites.",
                    callsite,
                    edge.source or "edge file",
                )
                continue
            by_callsite[callsite].append(resolved)

    return by_caller_fqn, by_callsite
