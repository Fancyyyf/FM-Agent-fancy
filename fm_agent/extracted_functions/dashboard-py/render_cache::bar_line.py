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
