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
