def _edge_from_mapping(item: dict, source: str) -> CallEdge:
    caller = _parse_caller(item.get("caller"), source)
    callee = _parse_callee(item.get("callee"), source)
    return CallEdge(
        caller=caller,
        callee=callee,
        source=_edge_source(item, source),
    )
