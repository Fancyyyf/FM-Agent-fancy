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
