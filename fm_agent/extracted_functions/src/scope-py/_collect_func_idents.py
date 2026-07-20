# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_collect_func_idents.py
#
# _collect_func_idents(node: ast.AST, source_lines: list[str]) -> tuple[set[str], set[str], set[str]]
#
# Pre-condition:
#   - node is an AST node rooted at a FunctionDef or AsyncFunctionDef with lineno and
#     end_lineno attributes set.
#   - source_lines is a list[str] containing every line of the source file that
#     produced node, in original order, with trailing newlines removed.
#
# Post-condition:
#   - Returns a 3‑tuple (idents, body_words, exc_types) where each element is a
#     set[str] whose members are lowercased. No returned set contains the empty string.
#   - idents contains every identifier whose value is read at least once within the
#     function body. An identifier whose value is read includes: any name resolved as a
#     value (Load context), the attribute name in any attribute‑access expression, and
#     any function‑parameter name that appears in the body in a value position.
#     Identifiers that only appear in write (Store) or deletion (Del) contexts are
#     excluded.
#   - body_words contains every distinct alphabetic word of at least 3 characters that
#     appears in the source text spanning from the function's first line through its
#     last line (inclusive), after excluding any word whose text originates inside a
#     comment, a string literal, or the docstring of the function.
#   - exc_types contains every exception type name that is either raised (via a raise
#     statement with a named exception instance or class), caught (via an except clause
#     that names a type), or otherwise referenced as an exception class anywhere within
#     the function body.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
