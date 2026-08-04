def render_cache(state):
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

    n_cr = state.totals.get("cache_read", 0)
    n_in = state.totals.get("input", 0) + state.totals.get("cache_write", 0)
    o_cr = state.opencode_token_totals.get("cache_read", 0)
    o_in = (state.opencode_token_totals.get("input", 0)
            + state.opencode_token_totals.get("cache_write", 0))
    total_cr = n_cr + o_cr
    total_input = n_in + o_in
    rows = list(state.cache_window)

    lines = [
        bar_line("latest 10", rows[-10:]),
        bar_line("latest 100", rows[-100:]),
        bar_line("overall", [(total_cr, total_cr + total_input)]),
        "[dim]coverage = cache_read / (input + cache_write + cache_read)[/]",
    ]

    # cost-savings estimate: cache_read tokens would otherwise have been
    # billed as fresh input (cache_write is its own cost, already in TOTAL).
    p = _price_for(state.model_seen or "")
    if p:
        in_per = p.get("input_cost_per_token") or 0
        cr_per = p.get("cache_read_input_token_cost") or 0
        if in_per > 0 and total_cr > 0:
            saved = total_cr * (in_per - cr_per)
            actual = state.cost_native + state.opencode_cost
            if saved > 0:
                pct = saved / (actual + saved) * 100 if actual + saved > 0 else 0
                lines.append(
                    f"[bold green]saved ~${saved:.2f} by cache[/]"
                    f"  [dim]({pct:.0f}% off no-cache)[/]"
                )

    if total_cr + total_input == 0:
        text = Text.from_markup("[dim](no token data yet)[/]")
    else:
        text = Text.from_markup("\n".join(lines))
    return Panel(Align.center(text, vertical="middle"),
                 title="Cache Coverage", border_style="green")
