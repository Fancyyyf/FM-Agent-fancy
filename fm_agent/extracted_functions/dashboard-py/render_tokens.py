# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/render_tokens.py
#
# render_tokens(state) -> RenderableType
#
# Pre-condition:
#   - state is a State instance
#   - state.totals is a dict-like mapping token-category keys ("input",
#     "cache_read", "cache_write", "output") to non-negative integer
#     counts representing verification-phase token consumption
#   - state.opencode_token_totals is a dict-like mapping the same four
#     token-category keys to non-negative integer counts representing
#     OpenCode token consumption
#   - state.model_seen is a string identifying the LLM model used, or
#     None / empty — used to derive per-token pricing
#   - state.cost_native is a numeric value representing the total
#     verification cost in the native currency unit
#   - state.opencode_cost is a numeric value representing the total
#     OpenCode cost in the same currency unit
#   - state.opencode_calls is a non-negative integer count of OpenCode
#     invocations made during the run
#
# Post-condition:
#   - Returns a Rich Panel renderable whose title is "Tokens & Cost"
#     and whose border is styled green
#   - The panel contains a table with exactly three data rows: one for
#     verification tokens, one for OpenCode tokens, and one for the
#     combined totals across both sources
#   - Each data row displays five values: the token count classified as
#     new input ("input"), the count of tokens served from the prompt
#     cache ("cache_read"), the count of tokens written to the prompt
#     cache ("cache_write"), the output token count ("output"), and a
#     monetary cost formatted as currency
#   - The OpenCode row label includes the value of state.opencode_calls
#     to indicate the number of invocations comprising the totals
#   - The combined-total row's token values are the element-wise sum of
#     the corresponding verification and OpenCode token counts; its cost
#     is the sum of the two cost values
#   - Token values are formatted with unit suffixes that compactly
#     represent large magnitudes; cost values are derived from per-model
#     pricing and formatted consistently with the currency unit
# [SPEC]

# [INFO]
# _price_for(model: str) -> dict
#   Pre-condition: model is a non-empty string identifying an LLM model
#   Post-condition: Returns a dict containing per-token pricing
#     information for the given model, with keys suitable for cost
#     computation from token counts
# [SPLIT]
# _fmt_tokens(count: int) -> str
#   Pre-condition: count is a non-negative integer
#   Post-condition: Returns a human-readable string representation of
#     count with an appropriate magnitude suffix (e.g., "k", "M") such
#     that the resulting string is compact and the value can be
#     approximately recovered
# [SPLIT]
# _fmt_cost(amount: float) -> str
#   Pre-condition: amount is a non-negative numeric value in the native
#     currency unit
#   Post-condition: Returns a human-readable currency-formatted string
#     representation of amount, consistent in precision and formatting
#     across all rows of the table
# [INFO]

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
