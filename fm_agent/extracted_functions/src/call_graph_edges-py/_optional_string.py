# [SPEC]
# Unit: src/call_graph_edges.py
#
# _optional_string(value, key: str, source: str) -> str
#
# Pre-condition:
#   - key is a non-empty string naming the data field being extracted
#   - source is a non-empty string identifying the origin of the input data
#   - value is the looked-up entry for the field named by key, which may be None (key absent), a str, or any other type
#
# Post-condition:
#   - Returns an empty string when value is None
#   - Returns a string whose content equals value with all leading and trailing whitespace characters removed when value is a str
#   - Raises ValueError whose error message contains source and key when value is not None and not a str
# [SPEC]

# [INFO]
# _clean_label(value: str) -> str
#   Pre-condition: value is a str
#   Post-condition: Returns value with all leading and trailing whitespace characters removed
# [INFO]

def _optional_string(value, key: str, source: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{source}: '{key}' must be a string")
    return _clean_label(value)
