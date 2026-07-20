# [SPEC]
# Unit: src/call_graph_edges.py
#
# _edge_source(item, fallback) -> str
#
# Pre-condition:
#   - item is a dict
#   - fallback is a string
#
# Post-condition:
#   - Returns a string identifying the edge origin
#   - When item contains a key "source" whose value is a string that is non-empty after stripping, returns that stripped string
#   - When no valid "source" value is present and item contains a key "evidence" whose value is a list, returns up to 4 elements from that list, each converted to a string and stripped, joined by "; ", provided at least one such element is non-empty after stripping
#   - When no valid "source" value is present and item contains a key "evidence" whose value is a string that is non-empty after stripping, returns that stripped string
#   - Otherwise, returns fallback unchanged
#   - Never raises an exception
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
