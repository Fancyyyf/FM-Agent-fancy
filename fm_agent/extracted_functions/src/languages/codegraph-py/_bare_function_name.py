# [SPEC]
# Unit: src/languages/codegraph.py
#
# _bare_function_name(name: str) -> str
#
# Pre-condition:
#   - name is a string that may be a raw function name, a scope-qualified name,
#     a decorated function signature (function-pointer or pointer-return syntax),
#     or an empty string
#
# Post-condition:
#   - Returns a string containing the bare, unqualified function identifier
#     extracted from name, with no surrounding syntactic decorations
#   - When name is empty or consists only of whitespace characters, returns the
#     empty string ""
#   - When name contains a scope qualifier — double-colon '::', member-access
#     dot '.', or a parenthesized receiver expression ending with '.' or ')' —
#     returns the rightmost identifier component after the last such separator
#   - When name is a function-pointer expression matching the pattern
#     '(*identifier)(...)' possibly followed by a parameter list, returns
#     the captured identifier
#   - When name starts with '*' followed by an identifier (pointer-return
#     syntax), returns that identifier
#   - When name starts with word characters (alphanumeric and underscore),
#     returns the maximal prefix of consecutive word characters
#   - Angle-bracket template parameters with their contents and parenthesized
#     parameter lists are excluded from the returned identifier
#   - When none of the recognized identifier patterns match and name is
#     non-empty, returns name unchanged
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _bare_function_name(name: str) -> str:
    """Extract the bare function identifier from a potentially decorated name.

    Tree-sitter sometimes stores a full function signature in the name column
    for macro-generated C/C++ declarations (e.g. ``(*func)(type *param)``
    instead of ``func``).  Strips decorations so the result can be used as a
    filename stem and call-edge key.

    Handled patterns (language-agnostic):
    - Simple identifier: ``"my_func"`` -> ``"my_func"``
    - Qualified name: ``"ns::Cls::method"`` -> ``"method"``
    - Go pointer receiver: ``"(*T).Method"`` -> ``"Method"``
    - Function-pointer: ``"(*func)(type *param)"`` -> ``"func"``
    - Pointer return: ``"*func_name(...)"`` -> ``"func_name"``
    - this-dot: ``"this.onClick"`` -> ``"onClick"``
    - Empty: ``""`` -> ``""`` (caller falls back to ``_function``)
    """
    name = name.strip()
    if not name:
        return ""

    m = re.search(r'(?:[:\.)])(\w+)$', name)
    if m:
        return m.group(1)
    m = re.match(r'\(\s*\*\s*(\w+)\s*\)', name)
    if m:
        return m.group(1)
    m = re.match(r'\*\s*(\w+)', name)
    if m:
        return m.group(1)
    m = re.match(r'^(\w+)', name)
    if m:
        return m.group(1)
    return name
