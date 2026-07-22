# [SPEC]
# Unit: src/languages/erlang.py
#
# _SourceIndex.source_for_range(self, lsp_range) -> str
#
# Pre-condition:
#   - self is a _SourceIndex instance whose .source attribute is a string and whose position resolution matches the encoding used for the character values in lsp_range
#   - lsp_range is a dict with keys 'start' and 'end', each being a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based UTF-16 code unit offset)
#   - The position described by lsp_range["start"] does not follow the position described by lsp_range["end"] in source order
#
# Post-condition:
#   - Returns the substring of self.source that spans from the byte offset corresponding to lsp_range["start"] (inclusive) to the byte offset corresponding to lsp_range["end"] (exclusive)
# [SPEC]

# [INFO]
# _SourceIndex.position_to_offset(self, position) -> int
#   Pre-condition: self is a _SourceIndex instance with indexed source; position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based UTF-16 code unit offset)
#   Post-condition: Returns the 0-based byte offset in self.source that corresponds to the given position, accounting for UTF-16 code unit encoding of characters
# [INFO]

    def source_for_range(self, lsp_range: dict) -> str:
        start = self.position_to_offset(lsp_range["start"])
        end = self.position_to_offset(lsp_range["end"])
        return self.source[start:end]
