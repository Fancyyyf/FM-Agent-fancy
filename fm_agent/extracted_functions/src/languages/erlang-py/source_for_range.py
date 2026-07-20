# [SPEC]
# Unit: src/languages/erlang-py/source_for_range.py
#
# _SourceIndex.source_for_range(lsp_range: dict) -> str
#
# Pre-condition:
#   - self is a _SourceIndex instance whose .source attribute is a string
#   - lsp_range is a dict with keys "start" and "end", each being a dict with keys "line"
#     (int, 0-based) and "character" (int, 0-based)
#   - The start position, when converted to a character offset in self.source, does not
#     exceed the character offset of the end position
#
# Post-condition:
#   - Returns the substring of self.source that spans from the character offset corresponding
#     to the line and character in lsp_range["start"] (inclusive) to the character offset
#     corresponding to the line and character in lsp_range["end"] (exclusive)
#   - The returned string preserves the exact byte content of the indexed source region,
#     including any whitespace or special characters within the range
# [SPEC]

# [INFO]
# self.position_to_offset(pos: dict) -> int
#   Pre-condition: pos is a dict with keys "line" (int, 0-based) and "character" (int, 0-based)
#     where line is within the bounds of self.source
#   Post-condition: Returns the 0-based character offset into self.source that corresponds to
#     the given line and character position, accounting for the fixed width of newline characters
#     between lines
# [INFO]

    def source_for_range(self, lsp_range: dict) -> str:
        start = self.position_to_offset(lsp_range["start"])
        end = self.position_to_offset(lsp_range["end"])
        return self.source[start:end]
