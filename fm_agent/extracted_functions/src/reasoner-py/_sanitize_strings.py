# [SPEC]
# Unit: src/reasoner-py/_sanitize_strings
#
# _sanitize_strings(obj) -> Any
#
# Pre-condition:
#   - obj is any Python value (str, dict, list, or any other type).
#
# Post-condition:
#   - Returns a structurally equivalent deep copy of obj with the following
#     transformation applied to every string value at any nesting depth:
#     each string is replaced by the result of encoding it as ASCII (ignoring
#     non-encodable characters) and decoding back to a str, effectively removing
#     all non-ASCII characters.
#   - dict keys are preserved as-is and their values are recursively processed.
#   - list elements are recursively processed in order.
#   - Values that are not str, dict, or list are returned unchanged.
#   - Does not mutate the input obj; dict/list containers are reconstructed.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _sanitize_strings(obj):
    """Remove non-ASCII characters from all string values in a dict/list."""
    if isinstance(obj, str):
        return obj.encode("ascii", "ignore").decode("ascii")
    if isinstance(obj, dict):
        return {k: _sanitize_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_strings(v) for v in obj]
    return obj
