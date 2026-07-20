# [SPEC]
# Unit: src/call_graph_edges.py
#
# _load_json_edges(text, source_path) -> list[CallEdge]
#
# Pre-condition:
#   - text is a string
#   - source_path is a string identifying the origin of the JSON content being
#     parsed
#
# Post-condition:
#   - When text is valid JSON that parses to an object containing an "edges"
#     key whose value is a list, returns a list of CallEdge objects, one per
#     element of that list, in the same order as the "edges" array
#   - When the "edges" list is empty, returns an empty list
#   - Every returned CallEdge has a callee whose fqn is a non-empty string
#   - Every returned CallEdge has a caller object where at least one of fqn
#     or callsite_names is non-empty
#   - When text is not valid JSON, raises ValueError with a message that
#     includes source_path
#   - When the parsed JSON value is not a dict, raises ValueError with a
#     message that includes source_path
#   - When the parsed dict does not contain an "edges" key whose value is a
#     list, raises ValueError with a message that includes source_path
#   - When any element of the "edges" list is not a dict, raises ValueError
#     with a message that includes source_path and the 1-based index of
#     the invalid element within the "edges" array
# [SPEC]

# [INFO]
# _edge_from_mapping(mapping, source) -> CallEdge
#   Pre-condition: mapping is a dict whose keys conform to the extra-edge JSON
#     schema (at minimum defining caller and callee fields); source is a
#     string identifying the location for error messages
#   Post-condition: Returns a CallEdge where callee.fqn is a non-empty string,
#     the caller has at least one of fqn or callsite_names non-empty, and
#     source is set from the mapping's evidence or the source context
# [INFO]

def _load_json_edges(text: str, source_path: str) -> list[CallEdge]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_path}: invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{source_path}: expected JSON object with an 'edges' list")
    if not isinstance(data.get("edges"), list):
        raise ValueError(f"{source_path}: expected an 'edges' list")

    edges = []
    for idx, item in enumerate(data["edges"], start=1):
        item_source = f"{source_path}:edges[{idx}]"
        if not isinstance(item, dict):
            raise ValueError(f"{item_source}: expected edge object")
        edges.append(_edge_from_mapping(item, item_source))
    return edges
