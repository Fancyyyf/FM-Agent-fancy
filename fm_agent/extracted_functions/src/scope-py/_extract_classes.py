def _extract_classes(tree: ast.Module,
                     source_lines: list[str]) -> list[dict]:
    """
    Return one dict per ClassDef with:
        name, lineno, end_lineno, docstring, method_linenos
    """
    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        doc = ast.get_docstring(node) or ''
        method_linenos = [
            n.lineno for n in ast.walk(node)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        classes.append({
            'name':          node.name,
            'lineno':        node.lineno,
            'end_lineno':    node.end_lineno,
            'docstring':     doc,
            'method_linenos': method_linenos,
        })
    return classes
