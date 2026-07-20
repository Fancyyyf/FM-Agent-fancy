# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/render_bugs.py
#
# render_bugs(state) -> Panel
#
# Pre-condition:
#   - state is a State instance whose bugs_confirmed,
#     bugs_not_confirmed, and bugs_pending attributes are non-negative
#     integers reflecting the current bug-validation verdict counts
#     from ingested trace data
#
# Post-condition:
#   - Returns a Rich Panel renderable whose body displays four labeled
#     numeric values: confirmed, not-confirmed, pending, and total
#   - The total displayed equals the sum bugs_confirmed +
#     bugs_not_confirmed + bugs_pending
#   - The panel title is "Bug Validation" with a yellow border
#   - The body text is vertically centered within the panel
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def render_bugs(state):
    total = state.bugs_confirmed + state.bugs_not_confirmed + state.bugs_pending
    text = Text.from_markup(
        f"[green]✓ confirmed[/]      {state.bugs_confirmed}\n"
        f"[yellow]✗ not_confirmed[/]  {state.bugs_not_confirmed}\n"
        f"[dim]… pending[/]         {state.bugs_pending}\n"
        f"[bold]total[/]             [bold]{total}[/]"
    )
    return Panel(Align.center(text, vertical="middle"),
                 title="Bug Validation", border_style="yellow")
