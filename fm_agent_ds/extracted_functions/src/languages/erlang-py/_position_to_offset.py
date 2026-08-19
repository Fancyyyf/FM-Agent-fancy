def _position_to_offset(source: str, position: dict) -> int:
    """Compatibility wrapper for callers that do not reuse a source index."""
    return _SourceIndex.build(source).position_to_offset(position)
