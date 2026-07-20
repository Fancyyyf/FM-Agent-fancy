# [SPEC]
# Unit: src/call_graph_edges.py
#
# normalize_fqn_label(label: str) -> str
#
# Pre-condition:
#   - label is a non-empty string
#
# Post-condition:
#   - Returns a canonical FQN string suitable for storage, lookup, and comparison
#   - The normalization is deterministic: the same input always produces the same output
#   - The returned FQN uses "::" as a component separator and replaces the source-file extension dot with "-"
# [SPEC]

# [INFO]
# _normalize_endpoint_label(label: str) -> str
#   Pre-condition: label is a non-empty string
#   Post-condition: Returns a canonical FQN string where "::" separates components and the source-file extension dot is replaced with "-"; the normalization is deterministic
# [INFO]

def normalize_fqn_label(label: str) -> str:
    """Normalize ``path/to/file.c::func`` into an FM-Agent FQN when needed."""
    return _normalize_endpoint_label(label)
