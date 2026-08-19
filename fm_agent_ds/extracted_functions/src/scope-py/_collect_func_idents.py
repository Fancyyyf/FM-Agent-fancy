def _collect_func_idents(node: ast.FunctionDef | ast.AsyncFunctionDef,
                          source_lines: list[str]) -> tuple[set[str], set[str], set[str]]:
    """Return (identifier_set, body_words_set, raised_exception_types)."""
    idents: set[str] = set()
    exc_types: set[str] = set()

    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            idents.add(n.id.lower())
        elif isinstance(n, ast.Attribute):
            idents.add(n.attr.lower())
        elif isinstance(n, ast.arg):
            idents.add(n.arg.lower())
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            for w in re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{2,}', n.value):
                idents.add(w.lower())
        # collect raised exception types
        elif isinstance(n, ast.Raise):
            if n.exc:
                exc_node = n.exc
                if isinstance(exc_node, ast.Call):
                    exc_node = exc_node.func
                if isinstance(exc_node, ast.Name):
                    exc_types.add(exc_node.id.lower())
                elif isinstance(exc_node, ast.Attribute):
                    exc_types.add(exc_node.attr.lower())
        # collect caught exception types
        elif isinstance(n, ast.ExceptHandler) and n.type:
            exc_node = n.type
            if isinstance(exc_node, ast.Name):
                exc_types.add(exc_node.id.lower())
            elif isinstance(exc_node, ast.Attribute):
                exc_types.add(exc_node.attr.lower())

    body_text = '\n'.join(source_lines[node.lineno - 1: node.end_lineno])
    body_words = {w for w in re.findall(r'\b([a-zA-Z]{4,})\b', body_text.lower())
                  if w not in _STOP}

    return idents, body_words, exc_types
