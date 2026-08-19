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
