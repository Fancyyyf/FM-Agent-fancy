# [SPEC]
# Unit: src/languages/erlang-py/_source_for_range.py
#
# _source_for_range(source, lsp_range) -> str
#
# Pre-condition:
#   - source is a string containing source code text
#   - lsp_range is a dict with keys 'start' and 'end', each being a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based)
#
# Post-condition:
#   - Returns the substring of source that spans from the start position (inclusive) to the end position (exclusive)
# [SPEC]

# [INFO]
# _SourceIndex.build(source) -> _SourceIndex
#   Pre-condition: source is a string
#   Post-condition: Returns a _SourceIndex instance whose operations are scoped to the given source string
# [SPLIT]
# _SourceIndex.source_for_range(lsp_range) -> str
#   Pre-condition: lsp_range is a dict with keys 'start' and 'end', each having 'line' (int, 0-based) and 'character' (int, 0-based) keys, and the start position does not follow the end position
#   Post-condition: Returns the substring of the indexed source that spans from the start position (inclusive) to the end position (exclusive)
# [INFO]

def _source_for_range(source: str, lsp_range: dict) -> str:
    """Compatibility wrapper for callers that do not reuse a source index."""
    return _SourceIndex.build(source).source_for_range(lsp_range)
