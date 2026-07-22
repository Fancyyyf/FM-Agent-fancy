# [SPEC]
# Unit: src/languages/codegraph.py
#
# _bare_function_name(name: str) -> str
#
# Pre-condition:
#   - name is a string that may be a raw function name, a scope-qualified name,
#     a decorated function signature (function-pointer or pointer-return syntax),
#     an operator overload name, or an empty string
#
# Post-condition:
#   - Returns a string containing the bare function identifier extracted from name,
#     following these rules in order:
#
#   1. Strips leading/trailing whitespace. If the result is empty, returns "".
#
#   2. Determines a "tail" string:
#      - Initially tail = name (after stripping).
#      - If tail contains "::", tail is set to the substring after the last "::",
#        with leading whitespace removed.
#      - Else if tail contains ".", tail is set to the substring after the last ".",
#        with leading whitespace removed.
#
#   3. Operator overload detection (applied to tail):
#      If tail starts with "operator":
#        - Let rest = tail[len("operator"):].lstrip()
#        - If rest starts with "[]", returns "operator[]".
#        - If rest starts with "()", returns "operator()".
#        - If rest matches the pattern "new" optionally followed by whitespace
#          and "[" whitespace "]", returns "operator new[]" if brackets are present,
#          otherwise "operator new".
#        - If rest matches the pattern "delete" optionally followed by whitespace
#          and "[" whitespace "]", returns "operator delete[]" if brackets are present,
#          otherwise "operator delete".
#        - Otherwise, collects consecutive characters from rest that are in the set
#          + - * / % & | ^ ~ ! = < > , and returns "operator" + the collected symbols.
#
#   4. If no operator result was produced, attempts the following regex matches on
#      the original stripped name (before tail modification):
#        a. `(?:^|::|\.)(\w+)$` — returns the rightmost identifier component
#           (sequence of word characters) preceded by start-of-string, "::", or ".".
#        b. `\(\s*\*\s*(\w+)\s*\)` — returns the identifier inside a
#           function-pointer expression like "(*func)(...)".
#        c. `\*\s*(\w+)` — returns the identifier after a leading "*" (pointer
#           return syntax).
#        d. `^(\w+)` — returns the leading sequence of word characters.
#
#   5. If none of the above matches, returns the stripped name unchanged.
#
#   - Because the extraction patterns use \w+, template parameter brackets (<...>)
#     and parenthesized parameter/argument lists are implicitly excluded from the
#     returned identifier, except for operator names where they are explicitly
#     included as part of the operator representation.
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
    - C++ operator overload: ``"Vec::operator=="`` -> ``"operator=="``
    - Function-pointer: ``"(*func)(type *param)"`` -> ``"func"``
    - Pointer return: ``"*func_name(...)"`` -> ``"func_name"``
    - this-dot: ``"this.onClick"`` -> ``"onClick"``
    - Empty: ``""`` -> ``""`` (caller falls back to ``_function``)
    """
    name = name.strip()
    if not name:
        return ""

    tail = name
    if "::" in tail:
        tail = tail.rsplit("::", 1)[1].lstrip()
    elif "." in tail:
        tail = tail.rsplit(".", 1)[1].lstrip()

    if tail.startswith("operator"):
        rest = tail[len("operator"):].lstrip()
        if rest.startswith("[]"):
            return "operator[]"
        if rest.startswith("()"):
            return "operator()"
        if re.fullmatch(r'new(?:\s*\[\s*\])?', rest):
            return "operator new[]" if "[" in rest else "operator new"
        if re.fullmatch(r'delete(?:\s*\[\s*\])?', rest):
            return "operator delete[]" if "[" in rest else "operator delete"

        symbol = []
        for ch in rest:
            if ch in "+-*/%&|^~!=<>,":
                symbol.append(ch)
            else:
                break
        if symbol:
            return "operator" + "".join(symbol)

    m = re.search(r'(?:^|::|\.)(\w+)$', name)
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
