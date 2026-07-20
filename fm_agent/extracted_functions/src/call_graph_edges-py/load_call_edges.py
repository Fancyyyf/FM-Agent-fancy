# [SPEC]
# Unit: src/call_graph_edges-py/load_call_edges.py
#
# load_call_edges(path: str | os.PathLike | None) -> list[CallEdge]
#
# Pre-condition:
#   - path is either None, or a str or os.PathLike referring to an existing file or directory on the filesystem
#
# Post-condition:
#   - When path is None: returns an empty list
#   - When path refers to a single file: returns all CallEdge objects contained in that file, with no duplicate CallEdge entries in the result
#   - When path refers to a directory: returns the concatenated CallEdge objects from every recognized edge file found
#     recursively under the directory, processed in sorted-path order, with no duplicate CallEdge entries in the result
#   - Each returned CallEdge has a callee FQN that is a non-empty string
#   - If the file or directory at path is inaccessible, unreadable, or contains malformed data, the corresponding
#     I/O or parse exception propagates to the caller
# [SPEC]

# [INFO]
# _is_edge_file(file_path: Path) -> bool
#   Pre-condition: file_path refers to an existing file
#   Post-condition: Returns True exactly when the file at file_path contains parseable CallEdge data
# _load_call_edge_file(file_path: Path) -> list[CallEdge]
#   Pre-condition: file_path refers to a file that _is_edge_file recognizes as containing CallEdge data
#   Post-condition: Returns a list of CallEdge objects parsed from the file, each satisfying that at least one of
#     caller FQN or caller callsite_names is non-empty, and callee FQN is non-empty
# _dedupe_edges(edges: list[CallEdge]) -> list[CallEdge]
#   Pre-condition: edges is a list of CallEdge objects
#   Post-condition: Returns a list containing exactly one occurrence of each distinct CallEdge present in edges,
#     preserving the relative order of first occurrences
# [INFO]

def load_call_edges(path: str | os.PathLike | None) -> list[CallEdge]:
    """Load supplemental call edges from a JSON file or directory."""
    if path is None:
        return []

    edge_path = Path(path)
    if edge_path.is_dir():
        edges = []
        for file_path in sorted(edge_path.rglob("*")):
            if file_path.is_file() and _is_edge_file(file_path):
                edges.extend(_load_call_edge_file(file_path))
        return _dedupe_edges(edges)

    return _dedupe_edges(_load_call_edge_file(edge_path))
