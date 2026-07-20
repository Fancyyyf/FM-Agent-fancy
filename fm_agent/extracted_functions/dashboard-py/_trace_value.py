# [SPEC]
# Unit: fm_agent/extracted_functions/dashboard-py/_trace_value.py
#
# _trace_value(d, *keys) -> Optional[str]
#
# Pre-condition:
#   - d is a mapping (dict) or a non-mapping value.
#   - keys is a sequence of string key names.
#
# Post-condition:
#   - If d is not a dict, returns None.
#   - Otherwise, for each key in keys in order, the function looks
#     up d for the key itself and for two variants obtained by
#     prepending "+" and "*" to the key. The value associated with
#     the first candidate key that is present in d is returned.
#   - Returns None when no candidate key (plain or prefixed) is
#     present in d.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _trace_value(d, *keys):
    """Read plain or opencode-trace delta-prefixed fields."""
    if not isinstance(d, dict):
        return None
    for key in keys:
        for candidate in (key, f"+{key}", f"*{key}"):
            if candidate in d:
                return d[candidate]
    return None
