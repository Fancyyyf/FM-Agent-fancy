# [SPEC]
# Unit: src/languages/erlang-py/_SourceIndex.py
#
# _SourceIndex.build(cls, source: str) -> _SourceIndex
#
# Pre-condition:
#   - source is a string
#
# Post-condition:
#   - Returns a _SourceIndex instance whose content is derived solely from source
#   - The returned index represents source as an ordered sequence of lines,
#     where line boundaries correspond to newline character positions in source
#   - For each line, the byte offset of its first character within source is
#     computable from the returned index
#   - The total number of bytes across all lines in the returned index equals
#     the length of source
# [SPEC]

    def build(cls, source: str) -> _SourceIndex:
        lines = source.splitlines(keepends=True)
        line_offsets = []
        offset = 0
        for line in lines:
            line_offsets.append(offset)
            offset += len(line)
        return cls(source=source, lines=lines, line_offsets=line_offsets)
