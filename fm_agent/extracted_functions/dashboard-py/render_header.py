# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/render_header.py
#
# render_header(state: State) -> RenderableType
#
# Pre-condition:
#   - state is a State instance with state.workdir, state.model_seen,
#     and state.elapsed() populated
#
# Post-condition:
#   - Returns a Panel renderable with a cyan border containing a
#     single line of metadata as its body
#   - The body line contains four items separated by bullet
#     characters, in order: the literal text "FM-Agent Dashboard", the
#     working directory from state.workdir, the model identifier from
#     state.model_seen (or "?" when model_seen is falsy or absent),
#     and the formatted elapsed duration derived from state.elapsed()
#   - All items after the dashboard title are styled dimmed relative
#     to the title
# [SPEC]

# [INFO]
# state.elapsed() -> float
#   Pre-condition: state was initialized with a known start timestamp
#   Post-condition: Returns the number of seconds elapsed since state
#     initialization
# [SPLIT]
# _fmt_duration(seconds) -> str
#   Pre-condition: seconds is a non-negative numeric value
#   Post-condition: Returns a human-readable string representation of
#     the duration using the largest appropriate unit (hours, minutes,
#     seconds)
# [INFO]

def render_header(state):
    parts = [
        f"[bold cyan]FM-Agent Dashboard[/]",
        f"[dim]workdir:[/] {state.workdir}",
        f"[dim]model:[/] {state.model_seen or '?'}",
        f"[dim]elapsed:[/] {_fmt_duration(state.elapsed())}",
    ]
    return Panel(Text.from_markup("  •  ".join(parts)), border_style="cyan")
