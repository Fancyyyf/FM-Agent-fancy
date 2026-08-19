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
