def _parse_python_file(src_path: Path) -> tuple[list[dict], list[str], list[dict]] | tuple[None, None, None]:
    """Parse a Python source file with the ast module (richest signal extraction)."""
    try:
        content = src_path.read_text(errors='replace')
        tree = ast.parse(content)
        source_lines = content.splitlines()
    except Exception as exc:
        logger.warning("Could not parse %s: %s", src_path, exc)
        return None, None, None

    funcs = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls = _collect_calls(node)
        idents, body_words, exc_types = _collect_func_idents(node, source_lines)
        docstring = ast.get_docstring(node) or ''
        funcs.append({
            'name':       node.name,
            'start':      node.lineno,
            'end':        node.end_lineno,
            'calls':      calls,
            'idents':     idents,
            'body_words': body_words,
            'exc_types':  exc_types,
            'docstring':  docstring,
        })

    classes = _extract_classes(tree, source_lines)
    return funcs, source_lines, classes
