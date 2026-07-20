# [SPEC]
# Unit: src/languages/erlang-py/_symbol_uri.py
#
# _symbol_uri(symbol, fallback) -> str
#
# Pre-condition:
#   - symbol is a dict-like mapping that may contain keys
#     "uri" (str) and "location" (a dict-like with optional
#     key "uri" mapping to a str)
#   - fallback is a string
#
# Post-condition:
#   - Returns a string value determined by the first of the
#     following that is both present and truthy, evaluated in
#     order:
#     1. The value mapped by key "uri" in symbol
#     2. The value mapped by key "uri" within the dict-like
#        value at symbol["location"] (treated as an empty dict
#        when symbol["location"] is absent or falsy)
#     3. fallback
#   - When neither "uri" key maps to a truthy value, returns
#     fallback exactly as given
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _symbol_uri(symbol: dict, fallback: str):
    return symbol.get("uri") or (symbol.get("location") or {}).get("uri") or fallback
