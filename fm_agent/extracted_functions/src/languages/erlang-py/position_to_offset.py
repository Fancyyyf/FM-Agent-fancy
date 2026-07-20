# [SPEC]
# Unit: src/languages/erlang-py/position_to_offset.py
#
# _SourceIndex.position_to_offset(position: dict) -> int
#
# Pre-condition:
#   - self is a _SourceIndex instance whose .lines attribute is a list of strings,
#     .line_offsets is a list of integers, and .source is a string
#   - position is a dict with keys 'line' (int, 0-based) and 'character' (int, 0-based)
#
# Post-condition:
#   - Returns a 0-based offset into self.source corresponding to the given (line, character)
#     position, where character is measured in UTF-16 code units (1 unit per BMP character,
#     2 units per supplementary-plane character with code point > U+FFFF)
#   - When position["line"] is not less than len(self.lines), returns len(self.source)
#   - When position["character"] exceeds the total UTF-16 code units of the line at
#     position["line"], returns the byte offset at the end of that line
#   - Negative line or character values in position are treated as 0
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
