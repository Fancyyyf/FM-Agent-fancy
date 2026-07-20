# [SPEC]
# Unit: src/languages/erlang-py/_symbol_line_span.py
#
# _symbol_line_span(symbol_range: dict) -> tuple[int, int]
#
# Pre-condition:
#   - symbol_range is a dict with keys "start" and "end", each a dict containing at
#     least a "line" key whose value is an integer. These represent an LSP Range:
#     a half-open interval [start, end) in 0-based line/character coordinates.
#
# Post-condition:
#   - Returns a tuple (start, end) where both values are non-negative 0-based
#     integers and start <= end
#   - The tuple represents an inclusive line span: the symbol occupies every line
#     from start through end inclusive
#   - start is the "start" position's line, clamped to a minimum of 0
#   - When the "end" position's character is non-zero, end is the "end" position's
#     line (clamped to a minimum of start), reflecting that the half-open LSP range
#     includes at least one character on that line
#   - When the "end" position's character is 0 and the end line is strictly greater
#     than start, end is one less than the "end" position's line, because a
#     character of 0 means the symbol occupies no part of that final line
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _symbol_line_span(symbol_range: dict) -> tuple[int, int]:
    """Convert an LSP half-open range to a 0-based inclusive line span."""
    start = max(0, int(symbol_range["start"].get("line", 0)))
    end_position = symbol_range["end"]
    end = max(start, int(end_position.get("line", start)))
    if end > start and int(end_position.get("character", 0)) == 0:
        end -= 1
    return start, end
