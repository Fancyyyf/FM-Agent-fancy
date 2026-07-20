# [SPEC]
# Unit: src/languages/erlang-py/build.py
#
# build(cls, source) -> _SourceIndex
#
# Pre-condition:
#   - source is a string containing the full text content of
#     a source file
#   - cls is a class type whose constructor accepts keyword
#     arguments for initializing a source index
#
# Post-condition:
#   - Returns an instance of cls initialized from source
#   - The returned instance supports mapping a
#     (start_line, end_line) line-number pair to the substring
#     of source spanning from the start line (inclusive) to
#     the end line (exclusive)
#   - The returned instance supports converting a
#     (line, character) position to a 0-based byte offset
#     within source
#   - Line-break characters in source are preserved exactly as
#     they appear in the input string
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def build(cls, source: str) -> _SourceIndex:
        lines = source.splitlines(keepends=True)
        line_offsets = []
        offset = 0
        for line in lines:
            line_offsets.append(offset)
            offset += len(line)
        return cls(source=source, lines=lines, line_offsets=line_offsets)
