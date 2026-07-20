# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/bar_line.py
#
# bar_line(label, rows) -> str
#
# Pre-condition:
#   - label is a non-empty string.
#   - rows is an iterable of (cache_read, total_input) numeric pairs
#     where cache_read and total_input are non-negative.
#
# Post-condition:
#   - When the total input tokens aggregated across rows is zero,
#     returns a Rich markup string indicating no data for the given
#     label.
#   - Otherwise, returns a Rich markup string containing:
#       * The label left-aligned to a fixed width.
#       * The cache-hit rate expressed as a percentage with one
#         decimal place, rendered in bold with a color determined
#         by the rate: green when ≥ 80%, yellow when ≥ 50%, and
#         red otherwise.
#       * A 20-character horizontal bar whose filled portion is
#         proportional to the hit rate (rendered with the same color
#         as the percentage), followed by the formatted cache-read
#         and total-input token counts separated by " / " in dim
#         style.
# [SPEC]

# [INFO]
# _cache_rate(rows) -> (float, int, int)
#   Pre-condition: rows is a sequence of (cache_read, total_input)
#     numeric pairs with non-negative values.
#   Post-condition: Returns a tuple (rate, total_cache_read,
#     total_input) where total_cache_read is the sum of all
#     cache_read values, total_input is the sum of all total_input
#     values, and rate is total_cache_read / total_input when
#     total_input > 0, or 0.0 when total_input == 0.
# [SPLIT]
# _fmt_tokens(n) -> str
#   Pre-condition: n is a non-negative integer or float.
#   Post-condition: Returns a human-readable string representation
#     of the token count, using abbreviated suffixes (e.g., "k" for
#     thousands) when the magnitude warrants it.
# [INFO]

    def bar_line(label, rows):
        rate, cr, tot = _cache_rate(rows)
        if tot == 0:
            return f"[dim]{label:<14}(no data)[/]"
        pct = rate * 100
        bar_w = 20
        filled = int(bar_w * rate)
        bar = "█" * filled + "░" * (bar_w - filled)
        color = "green" if pct >= 80 else ("yellow" if pct >= 50 else "red")
        return (
            f"{label:<10}[bold {color}]{pct:5.1f}%[/]  [{color}]{bar}[/] "
            f"[dim]{_fmt_tokens(cr)} / {_fmt_tokens(tot)}[/]"
        )
