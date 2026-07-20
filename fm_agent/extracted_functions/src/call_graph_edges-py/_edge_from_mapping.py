# [SPEC]
# Unit: src/call_graph_edges.py
#
# _edge_from_mapping(item, source) -> CallEdge
#
# Pre-condition:
#   - item is a dict
#   - source is a string
#
# Post-condition:
#   - Returns a CallEdge constructed from the caller, callee, and evidence data in item
#   - The returned CallEdge's callee.fqn is a non-empty string
#   - The returned CallEdge's caller has at least one of fqn or callsite_names non-empty
#   - The returned CallEdge's source is a string derived from the item's evidence entries when present, or from source otherwise
#   - When item does not contain a well-formed "caller" key with at least one non-empty field, raises an error whose message includes source
#   - When item does not contain a well-formed "callee" key with a non-empty fqn, raises an error whose message includes source
# [SPEC]

# [INFO]
# _parse_caller(caller_data, source) -> CallerSelector
#   Pre-condition: caller_data is the value of item["caller"] (a dict or None); source is a string
#   Post-condition: Returns a CallerSelector where at least one of fqn or callsite_names is non-empty when caller_data is a dict containing conforming fields; raises an error whose message includes source when caller_data is missing, is not a dict, or lacks the required fields
# [SPLIT]
# _parse_callee(callee_data, source) -> CalleeTarget
#   Pre-condition: callee_data is the value of item["callee"] (a dict or None); source is a string
#   Post-condition: Returns a CalleeTarget whose fqn is a non-empty string when callee_data is a dict containing a conforming "fqn" field; raises an error whose message includes source when callee_data is missing, is not a dict, or lacks a valid fqn
# [SPLIT]
# _edge_source(item, source) -> str
#   Pre-condition: item is a dict; source is a string
#   Post-condition: Returns a string identifying the origin of the edge; when item contains evidence data, the returned string incorporates that evidence; otherwise the returned string equals source
# [INFO]

def _edge_from_mapping(item: dict, source: str) -> CallEdge:
    caller = _parse_caller(item.get("caller"), source)
    callee = _parse_callee(item.get("callee"), source)
    return CallEdge(
        caller=caller,
        callee=callee,
        source=_edge_source(item, source),
    )
