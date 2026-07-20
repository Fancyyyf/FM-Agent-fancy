# [SPEC]
# Unit: src/languages/erlang-py/_position_to_offset.py
#
# _position_to_offset(source, position) -> int
#
# Pre-condition:
#   - source is a string containing source code text
#   - position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based)
#
# Post-condition:
#   - Returns the 0-based byte offset within source that corresponds to the given line and character
# [SPEC]

# [INFO]
# _SourceIndex.build(source) -> _SourceIndex
#   Pre-condition: source is a string
#   Post-condition: Returns a _SourceIndex instance whose operations are scoped to the given source string
# [SPLIT]
# _SourceIndex.position_to_offset(position) -> int
#   Pre-condition: position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based)
#   Post-condition: Returns the 0-based byte offset in the indexed source string that corresponds to the given position
# [INFO]

def _position_to_offset(source: str, position: dict) -> int:
    """Compatibility wrapper for callers that do not reuse a source index."""
    return _SourceIndex.build(source).position_to_offset(position)
