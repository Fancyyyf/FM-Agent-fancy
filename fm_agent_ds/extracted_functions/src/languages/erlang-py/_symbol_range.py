def _symbol_range(symbol: dict):
    if "range" in symbol:
        return symbol["range"]
    return (symbol.get("location") or {}).get("range")
