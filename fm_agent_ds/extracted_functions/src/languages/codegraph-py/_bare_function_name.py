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
