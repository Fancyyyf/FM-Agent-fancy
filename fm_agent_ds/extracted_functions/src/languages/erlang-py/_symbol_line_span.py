def _symbol_line_span(symbol_range: dict) -> tuple[int, int]:
    """Convert an LSP half-open range to a 0-based inclusive line span."""
    start = max(0, int(symbol_range["start"].get("line", 0)))
    end_position = symbol_range["end"]
    end = max(start, int(end_position.get("line", start)))
    if end > start and int(end_position.get("character", 0)) == 0:
        end -= 1
    return start, end
