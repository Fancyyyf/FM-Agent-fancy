# [SPEC]
# Unit: src/call_graph_edges-py/_is_edge_file.py
#
# _is_edge_file(file_path: Path) -> bool
#
# Pre-condition:
#   - file_path is a Path object referring to an existing file on the filesystem
#
# Post-condition:
#   - Returns True exactly when the file at file_path contains parseable CallEdge data
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _is_edge_file(path: Path) -> bool:
    return path.suffix.lower() == ".json"
