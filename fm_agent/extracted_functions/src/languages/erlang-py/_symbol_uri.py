def _symbol_uri(symbol: dict, fallback: str):
    return symbol.get("uri") or (symbol.get("location") or {}).get("uri") or fallback
