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
