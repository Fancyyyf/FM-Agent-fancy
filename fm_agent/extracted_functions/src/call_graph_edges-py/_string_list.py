# [SPEC]
# Unit: src/call_graph_edges.py
#
# _string_list(value, key: str, source: str) -> tuple[str, ...]
#
# Pre-condition:
#   - key is a string naming a field (used in error messages)
#   - source is a string identifying the data origin (used in error messages)
#
# Post-condition:
#   - When value is not a list, raises ValueError whose message includes source and key
#   - When value is a list and any element is not a string, raises ValueError whose message includes source and key
#   - Otherwise, returns a tuple containing the label-normalized form of every string element of value whose label-normalized form is non-blank
#   - The relative order of elements in the returned tuple preserves the relative order of the corresponding elements in value
# [SPEC]

# [INFO]
# _clean_label(item: str) -> str
#   Pre-condition: item is a string
#   Post-condition: Returns the label-normalized form of item; returns an empty or blank string when item contains no meaningful label content
# [INFO]

def _string_list(value, key: str, source: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{source}: '{key}' must be a string array")
    out = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, str):
            raise ValueError(f"{source}: {key}[{idx}] must be a string")
        label = _clean_label(item)
        if label:
            out.append(label)
    return tuple(out)
