# [SPEC]
# Unit: src/languages/codegraph.py
#
# _extraction_ident(name: str, qualified_name: str) -> str
#
# Pre-condition:
#   - name and qualified_name are strings obtained from the codegraph database for a single function or method node
#
# Post-condition:
#   - Returns a string composed of one or more components joined by the literal "::"
#   - When qualified_name is non-empty and its suffix equals name, the leading components of the returned string (all except the last) correspond, in order, to the scope qualifiers extracted from the prefix of qualified_name that precedes name
#   - When qualified_name is empty or its suffix does not equal name, the returned string consists of exactly one component
#   - The final component of the returned string is derived from name
#   - No component of the returned string contains any character that would be a directory separator in any filesystem
#   - No component of the returned string contains signature syntax, pointer syntax, or template syntax that may have been present in the raw database column values
#   - The same (name, qualified_name) pair always produces the same returned string
#   - The separator character ("." vs "::") used in qualified_name does not affect the set or order of scope components in the returned string
# [SPEC]

# [INFO]
# _qualified_parts(name: str, qualified_name: str) -> list
#   Pre-condition:
#     - name and qualified_name are strings
#   Post-condition:
#     - Returns a list of non-empty strings
#     - The last element of the returned list equals name
#     - When qualified_name is non-empty and has name as a suffix, the elements before the last are the scope qualifier components extracted from the prefix of qualified_name that precedes name, split on "::" or "."
#     - When qualified_name is empty or does not have name as a suffix, the returned list is [name]
#     - The character used as the scope separator in qualified_name ("." or "::") does not affect the set or order of components in the returned list
# [SPLIT]
# _bare_function_name(name: str) -> str
#   Pre-condition:
#     - name is a string
#   Post-condition:
#     - Returns the bare function identifier extracted from name
#     - When name is a simple identifier with no decorations, the returned string equals name with leading and trailing whitespace removed
#     - When name contains scope qualifiers, pointer receiver syntax, function-pointer syntax, pointer-return syntax, or template parameters, the returned string is the innermost function name with those decorations stripped
#     - When name contains an operator overload, the returned string is the normalized operator form
#     - When name is the empty string or consists only of whitespace, the returned string is the empty string
# [SPLIT]
# canonicalize(func_name: str) -> str
#   Pre-condition:
#     - func_name is a string
#   Post-condition:
#     - Returns a string that contains no characters invalid in filesystem path components
#     - When func_name contains no characters that are invalid in filesystem path components, the returned string equals func_name
#     - When func_name is the empty string, the returned string is the empty string
# [INFO]

def _extraction_ident(name: str, qualified_name: str) -> str:
    """Return the class-qualified, filesystem-safe identifier for a function.

    Each component is first stripped of any tree-sitter decoration by
    :func:`_bare_function_name` (codegraph occasionally stores a whole signature
    or template body in the name column — see issue #82, which would otherwise
    blow past the filesystem's filename limit), then passed through
    :func:`canonicalize` (so a class-scoped operator like ``Store::operator/``
    stays path/FQN-safe), then joined with ``::``. This single string is used both
    as a function's FQN tail and — with ``::`` turned into path separators — as its
    extracted-file location, so the call edges (via :func:`_node_fqn_map`) and the
    extracted files (via ``run_extraction`` + ``_file_to_fqn``) always agree.
    Examples: ``main`` -> ``"main"``; ``LocalStorage::Flush`` ->
    ``"LocalStorage::Flush"``.
    """
    return "::".join(
        canonicalize(_bare_function_name(p))
        for p in _qualified_parts(name, qualified_name)
    )
