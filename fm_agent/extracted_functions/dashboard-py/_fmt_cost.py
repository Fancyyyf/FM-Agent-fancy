def _fmt_cost(usd):
    if usd is None:
        return "—"
    a = abs(usd)
    if a < 1:    return f"${usd:.3f}"
    if a < 100:  return f"${usd:.2f}"
    if a < 10000: return f"${usd:.1f}"
    return f"${usd:.0f}"
