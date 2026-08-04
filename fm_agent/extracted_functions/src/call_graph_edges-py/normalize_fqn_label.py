def normalize_fqn_label(label: str) -> str:
    """Normalize ``path/to/file.c::func`` into an FM-Agent FQN when needed."""
    return _normalize_endpoint_label(label)
