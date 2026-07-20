# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/render_cache.py
#
# render_cache(state: State) -> RenderableType
#
# Pre-condition:
#   - state is a State instance whose token-total fields (totals,
#     opencode_token_totals) contain numeric values keyed by category
#     strings
#   - state.cache_window is a sequence of (cache_read, total_input)
#     numeric pairs representing recent trace data
#   - state.model_seen is a string or None
#   - state.cost_native and state.opencode_cost are numeric values
#
# Post-condition:
#   - Returns a Panel renderable titled "Cache Coverage" with a green
#     border
#   - The panel body displays cache hit-rate bars for three
#     aggregation windows: the most recent 10 entries of
#     state.cache_window, the most recent 100 entries, and the
#     aggregate of all entries in state.cache_window
#   - Each bar renders a percentage value, a filled-bar visual of
#     width 20 characters, and the token counts in the form
#     "cache_read / total_input"
#   - The bar color is green when the hit rate is at least 80%,
#     yellow when at least 50%, and red when the hit rate is below 50%
#   - A window whose total_input is zero produces "(no data)" in place
#     of bar content for that window
#   - When the combined total of cache_read and input tokens across
#     all data sources is zero, the panel body displays "(no token
#     data yet)"
#   - Total cache_read tokens are computed as
#     state.totals["cache_read"] +
#     state.opencode_token_totals["cache_read"]
#   - Total input tokens are computed as
#     state.totals["input"] + state.totals["cache_write"] +
#     state.opencode_token_totals["input"] +
#     state.opencode_token_totals["cache_write"]
#   - The coverage (hit-rate) interpretation displayed below the bars
#     is: cache_read / (input + cache_write + cache_read)
#   - When pricing data is available for the model identified by
#     state.model_seen and total cache_read > 0, an additional line
#     shows estimated cost savings as a dollar amount and as a
#     percentage of what the total cost would have been without cache
#     reads
#   - The panel content is vertically centered
# [SPEC]

# [INFO]
# _cache_rate(rows) -> (float, int, int)
#   Pre-condition: rows is an iterable of (cache_read, total_input)
#     numeric pairs
#   Post-condition: Returns (rate, total_cache_read, total_input)
#     where rate = total_cache_read / total_input when total_input > 0,
#     and rate = 0 when total_input is 0
# [SPLIT]
# _fmt_tokens(n) -> str
#   Pre-condition: n is a non-negative integer
#   Post-condition: Returns a short human-readable string
#     representation of the token count n
# [SPLIT]
# _price_for(model) -> Optional[dict]
#   Pre-condition: model is a string (may be empty)
#   Post-condition: Returns a dict with keys "input_cost_per_token"
#     and "cache_read_input_token_cost" whose values are per-token
#     costs in dollars; returns None if no pricing data is known for
#     the given model identifier
# [INFO]

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
