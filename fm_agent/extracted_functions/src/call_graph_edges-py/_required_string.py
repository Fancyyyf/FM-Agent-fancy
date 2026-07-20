# [SPEC]
# Unit: src/call_graph_edges.py
#
# _required_string(value, key: str, source: str) -> str
#
# Pre-condition:
#   - key is a non-empty string naming the required data field
#   - source is a non-empty string identifying the origin of the input data
#   - value is the looked-up entry for the field named by key, which may be None (key absent), a str, or any other type
#
# Post-condition:
#   - Raises ValueError whose error message contains source and key when value is None, not a str, or a str that consists entirely of whitespace after stripping
#   - Returns a non-empty string whose content equals value with all leading and trailing whitespace characters removed when value is a str containing at least one non-whitespace character
# [SPEC]

# [INFO]
# _clean_label(value: str) -> str
#   Pre-condition: value is a str
#   Post-condition: Returns value with all leading and trailing whitespace characters removed
# [INFO]

def _required_string(value, key: str, source: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source}: missing non-empty string '{key}'")
    return _clean_label(value)
