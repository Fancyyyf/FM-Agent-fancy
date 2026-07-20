# [SPEC]
# Unit: src/languages/erlang-py/_symbol_range.py
#
# _symbol_range(symbol: dict) -> dict | None
#
# Pre-condition:
#   - symbol is a dict representing an LSP symbol, which may be either a
#     DocumentSymbol (containing a "range" key directly) or a SymbolInformation
#     (containing a "location" key which itself contains a "range")
#
# Post-condition:
#   - Returns the "range" value associated with the symbol, or None when no range
#     can be located
#   - When symbol contains a "range" key, returns its value
#   - When symbol lacks a "range" key but contains a truthy "location" key, returns
#     the "range" value from that location
#   - When symbol lacks both a "range" key and a truthy "location" key containing a
#     "range", returns None
#   - The returned value is the raw range dict without transformation
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _symbol_range(symbol: dict):
    if "range" in symbol:
        return symbol["range"]
    return (symbol.get("location") or {}).get("range")
