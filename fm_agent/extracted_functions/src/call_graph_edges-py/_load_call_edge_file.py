def _load_call_edge_file(edge_path: Path) -> list[CallEdge]:
    text = edge_path.read_text(errors="replace")
    if not text.strip():
        return []
    return _load_json_edges(text, str(edge_path))
