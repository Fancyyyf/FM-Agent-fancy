# [SPEC]
# Unit: src/call_graph_edges-py/_load_call_edge_file.py
#
# _load_call_edge_file(edge_path) -> list[CallEdge]
#
# Pre-condition:
#   - edge_path is a pathlib.Path referring to an existing file on the filesystem
#
# Post-condition:
#   - When the file content at edge_path is empty or consists entirely of whitespace
#     characters, returns an empty list
#   - When the file content at edge_path is non-empty, returns a list of CallEdge objects
#     parsed from the file's JSON content
#   - Each returned CallEdge has a callee whose fqn is a non-empty string
#   - If the file at edge_path is unreadable or contains text that is not valid JSON
#     conforming to the CallEdge schema, the corresponding I/O exception or JSON decoding
#     exception propagates to the caller
# [SPEC]

# [INFO]
# _load_json_edges(text, source) -> list[CallEdge]
#   Pre-condition: text is a non-empty string containing valid JSON that conforms to the
#     extra-edge JSON schema; source is a string identifying the origin file path
#   Post-condition: Returns a list of CallEdge objects deserialized from the JSON text;
#     each CallEdge has a caller (with at least one of fqn or callsite_names non-empty)
#     and a callee (with a non-empty fqn)
# [INFO]

def _load_call_edge_file(edge_path: Path) -> list[CallEdge]:
    text = edge_path.read_text(errors="replace")
    if not text.strip():
        return []
    return _load_json_edges(text, str(edge_path))
