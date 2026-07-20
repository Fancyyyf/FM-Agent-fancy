# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/render_llm_status.py
#
# render_llm_status(state) -> RenderableType
#
# Pre-condition:
#   - state.llm_statuses is an iterable where each element supports .get("code"),
#     .get("status"), .get("time"), .get("source"), and .get("label")
#   - Each element's "code" is an integer HTTP status code and "status" is a
#     string label
#
# Post-condition:
#   - Returns a Rich Panel renderable titled "LLM Calls" with a cyan border
#     style
#   - When state.llm_statuses yields no items: the panel body contains a
#     vertically centered, dimmed "(no LLM calls yet)" message
#   - When state.llm_statuses yields one or more items:
#     - The panel body opens with a summary line reporting the count of
#       status entries considered (capped at LLM_STATUS_WINDOW) and the
#       percentage of entries whose code maps to a 200-class label,
#       color-coded green when the percentage is 95% or above, yellow when
#       it is 80% or above but below 95%, and red when it is below 80%
#     - Below the summary, a single-line strip of colored block characters
#       represents the most recent status entries, with each character's
#       color determined by the entry's code and status via
#       _llm_status_style
#     - Below the strip, a table lists at most the 6 most recent entries
#       in reverse chronological order with columns: time, source, the
#       colored HTTP status code label, and a display label
#   - The returned renderable performs no I/O and is suitable for
#     composition into a terminal layout
# [SPEC]

# [INFO]
# _llm_status_style(code, status) -> (str, str)
#   Pre-condition: code is an integer HTTP status code; status is a string
#   Post-condition: Returns a pair (color, label) where color is a
#     Rich-compatible color name and label is a display string derived
#     from the code; entries whose code is 200 map to a distinct success
#     color and label that differentiates them from non-200 entries
# [INFO]

def render_llm_status(state):
    statuses = list(state.llm_statuses)[-LLM_STATUS_WINDOW:]
    if not statuses:
        return Panel(
            Align.center(Text.from_markup("[dim](no LLM calls yet)[/]"), vertical="middle"),
            title="LLM Calls",
            border_style="cyan",
        )

    strip = Text()
    for item in statuses[-50:]:
        color, label = _llm_status_style(item.get("code"), item.get("status"))
        symbol = "■" if label == "200" else "▲" if color == "yellow" else "■"
        strip.append(symbol, style=color)

    table = Table(show_header=True, header_style="bold", expand=True, pad_edge=False)
    table.add_column("time", style="dim", no_wrap=True)
    table.add_column("src", style="cyan", no_wrap=True)
    table.add_column("code", no_wrap=True)
    table.add_column("call", overflow="ellipsis", no_wrap=True)
    for item in list(reversed(statuses[-6:])):
        color, label = _llm_status_style(item.get("code"), item.get("status"))
        table.add_row(
            item.get("time") or "",
            item.get("source") or "?",
            f"[{color}]{label}[/]",
            item.get("label") or "",
        )

    total = len(statuses)
    ok = sum(1 for item in statuses if _llm_status_style(item.get("code"), item.get("status"))[1] == "200")
    rate = ok / total * 100 if total else 0
    text = Text.from_markup(
        f"[dim]recent {total}/{LLM_STATUS_WINDOW} calls[/]  "
        f"[bold {'green' if rate >= 95 else 'yellow' if rate >= 80 else 'red'}]{rate:.1f}% 200[/]\n"
    )
    text.append(strip)
    group = Table.grid(expand=True)
    group.add_row(text)
    group.add_row(table)
    return Panel(group, title="LLM Calls", border_style="cyan")
