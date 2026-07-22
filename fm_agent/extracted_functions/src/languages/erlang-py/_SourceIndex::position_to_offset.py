# [SPEC]
# Unit: src/languages/erlang.py
#
# _SourceIndex.position_to_offset(self, position) -> int
#
# Pre-condition:
#   - self is a _SourceIndex instance whose .source, .lines, and .line_offsets are initialized and mutually consistent: for each i, self.line_offsets[i] is the 0-based byte offset of the start of self.lines[i] within self.source
#   - position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based UTF-16 code unit offset)
#
# Post-condition:
#   - When the line number is not less than the number of indexed lines (len(self.lines)), returns len(self.source)
#   - Otherwise, returns the 0-based byte offset within self.source that corresponds to the given position, where the character offset counts UTF-16 code units:
#     * Each Unicode code point above U+FFFF (supplementary-plane character) contributes 2 UTF-16 code units
#     * All other code points contribute 1 UTF-16 code unit
#     * When the character offset exceeds the total UTF-16 code unit length of the line, the returned offset corresponds to the byte position at the end of that line
# [SPEC]

    def position_to_offset(self, position: dict) -> int:
        line_number = max(0, int(position.get("line", 0)))
        utf16_target = max(0, int(position.get("character", 0)))
        if line_number >= len(self.lines):
            return len(self.source)
        base = self.line_offsets[line_number]
        line = self.lines[line_number]
        units = 0
        index = 0
        while index < len(line) and units < utf16_target:
            char_units = 2 if ord(line[index]) > 0xFFFF else 1
            if units + char_units > utf16_target:
                break
            units += char_units
            index += 1
        return base + index
