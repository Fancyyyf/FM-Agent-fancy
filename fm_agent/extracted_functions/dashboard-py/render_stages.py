# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/render_stages.py
#
# render_stages(state) -> RenderableType
#
# Pre-condition:
#   - state is a State instance whose stage_counts attribute is a dict-like
#     mapping from stage name strings to dicts that map verdict category keys
#     ("success", "mismatch", "error", "format_error") to non-negative
#     integer counts
#   - STAGES is an iterable of stage name strings providing the display
#     order; every element of STAGES is a key in stage_counts or defaults
#     to zero for all verdict categories
#
# Post-condition:
#   - Returns a Rich Panel renderable whose title is "Stages" and whose
#     border is styled cyan
#   - The panel contains a table with one row for each stage name in
#     STAGES, in iteration order, and no other rows
#   - For each stage, the row displays four non-negative integer counts
#     derived from state.stage_counts: the number of successful
#     verifications (key "success"), mismatches (key "mismatch"), errors
#     (key "error"), and format errors (key "format_error")
#   - When a stage name is absent from state.stage_counts, every verdict
#     count for that stage is rendered as zero
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def render_stages(state):
    table = Table(show_header=True, header_style="bold", expand=True, pad_edge=False)
    table.add_column("Stage", style="cyan", no_wrap=True)
    table.add_column("✓", justify="right", style="green")
    table.add_column("⚠ mismatch", justify="right", style="yellow")
    table.add_column("✗ error", justify="right", style="red")
    table.add_column("fmt", justify="right", style="magenta")
    for st in STAGES:
        counts = state.stage_counts.get(st, {})
        table.add_row(
            st,
            str(counts.get("success", 0)),
            str(counts.get("mismatch", 0)),
            str(counts.get("error", 0)),
            str(counts.get("format_error", 0)),
        )
    return Panel(table, title="Stages", border_style="cyan")
