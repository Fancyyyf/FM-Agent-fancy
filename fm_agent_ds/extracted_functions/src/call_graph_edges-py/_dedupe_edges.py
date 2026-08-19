def _dedupe_edges(edges: Iterable[CallEdge]) -> list[CallEdge]:
    merged = {}
    for edge in edges:
        key = (
            edge.caller.fqn,
            edge.callee.fqn,
        )
        if key not in merged:
            merged[key] = {
                "fqn": edge.caller.fqn,
                "callsite_names": list(edge.caller.callsite_names),
                "source": edge.source,
                "info_names": list(edge.callee.info_names),
            }
            continue
        for name in edge.caller.callsite_names:
            if name not in merged[key]["callsite_names"]:
                merged[key]["callsite_names"].append(name)
        for name in edge.callee.info_names:
            if name not in merged[key]["info_names"]:
                merged[key]["info_names"].append(name)

    result = []
    for (_caller_fqn, callee_fqn), data in sorted(merged.items()):
        result.append(
            CallEdge(
                caller=CallerSelector(
                    fqn=data["fqn"],
                    callsite_names=tuple(data["callsite_names"]),
                ),
                callee=CalleeTarget(
                    fqn=callee_fqn,
                    info_names=tuple(data["info_names"]),
                ),
                source=data["source"],
            )
        )
    return result
