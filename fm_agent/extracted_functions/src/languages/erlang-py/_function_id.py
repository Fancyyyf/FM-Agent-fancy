# [SPEC]
# Unit: src/languages/erlang-py/_function_id.py
#
# _function_id(uri: str, label: str) -> str
#
# Pre-condition:
#   - uri is a string convertible to a filesystem path
#   - label is a string of the form "<name>/<arity>" where <name> is a
#     non-empty function name and <arity> is a non-negative integer
#     represented as a decimal string; the "/" delimiter must appear at
#     least once when scanning from the right side of label
#
# Post-condition:
#   - Returns a function identifier string of the form
#     "<module>__<unqualified_name>__<arity>" where:
#       - <module> is the escaped module identifier derived from uri
#       - <unqualified_name> is the escaped function name with any
#         colon-separated module qualifier prefix stripped (unless the
#         name starts with a single-quote character, in which case the
#         full name including the prefix is preserved)
#       - <arity> is the exact decimal string from label (after the last
#         "/"), stripped of any leading sign
#   - The double-underscore ("__") separator between <module>,
#     <unqualified_name>, and <arity> is unambiguous for splitting the
#     identifier back into its three components
#   - Raises ValueError when label does not contain a "/" character, or
#     when the substring after the last "/" is not parsable as an integer
#     (including empty string, non-numeric characters, or values with a
#     fractional part)
# [SPEC]

# [INFO]
# _module_from_uri(uri: str) -> str
#   Pre-condition: uri is a string convertible to a filesystem path
#   Post-condition: Returns a module identifier string derived from the
#     URI that contains no instances of the double-underscore sequence
#     ("__") and is non-empty
# [SPLIT]
# _escape_component(component: str) -> str
#   Pre-condition: component is a string
#   Post-condition: Returns the component with any character sequences
#     that would conflict with the double-underscore ("__") separator used
#     in FQN construction replaced or escaped; the returned string
#     contains no occurrences of "__" and is non-empty when the input
#     component is non-empty
# [INFO]

def _function_id(uri: str, label: str) -> str:
    try:
        name, arity = label.rsplit("/", 1)
        int(arity)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"ELP function label has no valid arity: {label!r}") from exc
    if ":" in name and not name.startswith("'"):
        name = name.rsplit(":", 1)[1]
    module = _module_from_uri(uri)
    return f"{_escape_component(module)}__{_escape_component(name)}__{arity}"
