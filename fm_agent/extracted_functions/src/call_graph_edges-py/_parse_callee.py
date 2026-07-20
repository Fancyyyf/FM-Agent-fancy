# [SPEC]
# Unit: src/call_graph_edges.py
#
# _parse_callee(value, source) -> CalleeTarget
#
# Pre-condition:
#   - value is the callee data to parse (a dict, or any value that may result from dict access)
#   - source is a string identifying the origin of the data for error reporting
#
# Post-condition:
#   - Returns a CalleeTarget constructed from the callee data
#   - The returned CalleeTarget.fqn is a non-empty string
#   - The returned CalleeTarget.info_names is a (possibly empty) tuple of strings
#   - When value is not a dict, raises a ValueError whose message includes source
#   - When value is a dict but does not contain a well-formed "fqn" field yielding a non-empty string, raises an error whose message includes source
# [SPEC]

# [INFO]
# _required_string(val, field_name, source) -> str
#   Pre-condition: val is a dict lookup result (may be None, str, or other); field_name is a string naming the field; source is a string identifying the data origin
#   Post-condition: Returns a non-empty string when val is a string that is non-empty after stripping whitespace; raises an error whose message includes source and field_name when val is None, not a string, or whitespace-only
# [SPLIT]
# _string_list(val, field_name, source) -> tuple[str, ...]
#   Pre-condition: val is a list of strings or an empty list; field_name is a string naming the field; source is a string identifying the data origin
#   Post-condition: Returns a (possibly empty) tuple of strings corresponding to the elements of val; raises an error whose message includes source and field_name when val is not a list
# [INFO]

def _parse_callee(value, source: str) -> CalleeTarget:
    if not isinstance(value, dict):
        raise ValueError(f"{source}: missing object 'callee'")

    fqn = _required_string(value.get("fqn"), "callee.fqn", source)
    info_names = _string_list(value.get("info_names", []), "callee.info_names", source)
    return CalleeTarget(fqn=fqn, info_names=info_names)
