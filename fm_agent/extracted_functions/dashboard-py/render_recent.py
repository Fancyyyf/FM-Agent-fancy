# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/render_recent.py
#
# render_recent(state) -> RenderableType
#
# Pre-condition:
#   - state.recent_events is an iterable yielding 4-element tuples of the
#     form (time: str, stage: str, status: str, summary: str)
#
# Post-condition:
#   - Returns a Rich Panel renderable titled "Recent Events" with a cyan
#     border style
#   - The panel body is a table with four columns: time (dimmed style),
#     stage (cyan style), status (color-coded), and summary (ellipsized if
#     content exceeds column width)
#   - Each row corresponds to one tuple from state.recent_events in the
#     iteration order of that collection
#   - The status column renders each status value in a color determined by
#     its string: "success" → green, "mismatch" → yellow, "error" → red,
#     "format_error" → magenta, and any unrecognized status string → white
#   - The returned renderable performs no I/O and is suitable for
#     composition into a terminal layout
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def render_recent(state):
    table = Table(show_header=True, header_style="bold", expand=True, pad_edge=False)
    table.add_column("time", style="dim", no_wrap=True)
    table.add_column("stage", style="cyan", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("summary", overflow="ellipsis", no_wrap=True)
    for when, stage, status, summary in list(state.recent_events):
        color = {
            "success": "green",
            "mismatch": "yellow",
            "error": "red",
            "format_error": "magenta",
        }.get(status, "white")
        table.add_row(when, stage, f"[{color}]{status}[/]", summary)
    return Panel(table, title="Recent Events", border_style="cyan")
