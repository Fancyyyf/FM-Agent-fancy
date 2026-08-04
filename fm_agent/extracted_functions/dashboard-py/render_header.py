def render_header(state):
    parts = [
        f"[bold cyan]FM-Agent Dashboard[/]",
        f"[dim]workdir:[/] {state.workdir}",
        f"[dim]model:[/] {state.model_seen or '?'}",
        f"[dim]elapsed:[/] {_fmt_duration(state.elapsed())}",
    ]
    return Panel(Text.from_markup("  •  ".join(parts)), border_style="cyan")
