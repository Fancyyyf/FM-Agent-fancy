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
