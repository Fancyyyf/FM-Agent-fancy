def _is_edge_file(path: Path) -> bool:
    return path.suffix.lower() == ".json"
