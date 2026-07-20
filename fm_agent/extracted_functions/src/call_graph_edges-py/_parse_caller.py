# [SPEC]
# Unit: src/call_graph_edges.py
#
# _parse_caller(value, source: str) -> CallerSelector
#
# Pre-condition:
#   - value is the value of a "caller" key from caller input data (a dict or None)
#   - source is a string identifying the origin of the input (used in error messages)
#
# Post-condition:
#   - When value is not a dict, raises ValueError whose message contains source
#   - When value is a dict but neither a non-empty fqn string nor a non-empty callsite_names list can be extracted from it, raises ValueError whose message contains source
#   - Otherwise, returns a CallerSelector where at least one of fqn or callsite_names is non-empty
#   - The returned CallerSelector's fqn is the canonical normalized form of the string from value["fqn"] when that key holds a non-empty string; otherwise fqn is the empty string
#   - The returned CallerSelector's callsite_names is a tuple containing every non-empty string element from value["callsite_names"] when that key holds a list value; otherwise callsite_names is an empty tuple
# [SPEC]

# [INFO]
# _optional_string(value: dict, field: str, source: str) -> str
#   Pre-condition: value is a dict; field is a dotted key path; source is a context string
#   Post-condition: Returns the trimmed string of value[field] when it is a non-empty string; returns the empty string when the key is absent or its value is an empty string; raises ValueError when the value exists but is not a string
# [SPLIT]
# _string_list(value: list, field: str, source: str) -> tuple[str, ...]
#   Pre-condition: value is a list; field is a dotted key path; source is a context string
#   Post-condition: Returns a tuple of the trimmed string representations of every element in value, omitting empty values; raises ValueError when any element is not a string
# [SPLIT]
# normalize_fqn_label(fqn: str) -> str
#   Pre-condition: fqn is a non-empty string representing a function name with optional path components
#   Post-condition: Returns the canonical normalized FQN suitable for storage, lookup, and comparison
# [INFO]

def _parse_caller(value, source: str) -> CallerSelector:
    if not isinstance(value, dict):
        raise ValueError(f"{source}: missing object 'caller'")

    fqn = _optional_string(value.get("fqn", ""), "caller.fqn", source)
    if fqn:
        fqn = normalize_fqn_label(fqn)
    callsite_names = _string_list(
        value.get("callsite_names", []), "caller.callsite_names", source
    )

    if not fqn and not callsite_names:
        raise ValueError(
            f"{source}: at least one of 'caller.fqn' or "
            "'caller.callsite_names' must be non-empty"
        )

    return CallerSelector(fqn=fqn, callsite_names=callsite_names)
