def _source_for_range(source: str, lsp_range: dict) -> str:
    """Compatibility wrapper for callers that do not reuse a source index."""
    return _SourceIndex.build(source).source_for_range(lsp_range)
