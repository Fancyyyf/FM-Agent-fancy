def _edge_source(item: dict, fallback: str) -> str:
    source = item.get("source")
    if isinstance(source, str) and source.strip():
        return source.strip()

    evidence = item.get("evidence")
    if isinstance(evidence, list):
        values = [str(value).strip() for value in evidence if str(value).strip()]
        if values:
            return "; ".join(values[:4])
    if isinstance(evidence, str) and evidence.strip():
        return evidence.strip()
    return fallback
