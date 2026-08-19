def render_tokens(state):
    p = _price_for(state.model_seen or "")
    table = Table(show_header=True, header_style="bold", expand=True, pad_edge=False)
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("in:new", justify="right")
    table.add_column("in:read", justify="right", style="green")
    table.add_column("in:write", justify="right", style="yellow")
    table.add_column("output", justify="right")
    table.add_column("cost", justify="right", style="bold")

    def row(label, b):
        return [
            label,
            _fmt_tokens(b.get("input", 0)),
            _fmt_tokens(b.get("cache_read", 0)),
            _fmt_tokens(b.get("cache_write", 0)),
            _fmt_tokens(b.get("output", 0)),
        ]

    table.add_row(*row("verification", state.totals), _fmt_cost(state.cost_native))
    table.add_row(
        *row(f"opencode ({state.opencode_calls})", state.opencode_token_totals),
        _fmt_cost(state.opencode_cost),
    )
    # TOTAL — sum across both sources; also expose total input in the label
    sums = {k: state.totals.get(k, 0) + state.opencode_token_totals.get(k, 0)
            for k in ("input", "cache_read", "cache_write", "output")}
    in_total = sums["input"] + sums["cache_read"] + sums["cache_write"]
    table.add_row(
        f"[bold]TOTAL[/] [dim](in={_fmt_tokens(in_total)})[/]",
        _fmt_tokens(sums["input"]),
        _fmt_tokens(sums["cache_read"]),
        _fmt_tokens(sums["cache_write"]),
        _fmt_tokens(sums["output"]),
        f"[bold]{_fmt_cost(state.cost_native + state.opencode_cost)}[/]",
    )
    return Panel(table, title="Tokens & Cost", border_style="green")
