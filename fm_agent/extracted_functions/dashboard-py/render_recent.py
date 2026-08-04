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
