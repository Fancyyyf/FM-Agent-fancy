# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_parse_python_file.py
#
# _parse_python_file(src_path: Path) -> tuple[list[dict], list[str], list[dict]] | tuple[None, None, None]
#
# Pre-condition:
#   - src_path is a Path to a Python source file that exists on disk and is readable.
#
# Post-condition:
#   - If the source text is syntactically valid Python and can be parsed into an AST
#     without raising an exception, returns a 3‑tuple (funcs_info, source_lines, classes)
#     where:
#       * funcs_info is a list of dicts, one per function defined at module scope.
#         Each dict contains at minimum the following keys:
#           - 'name' (str): the function name as written in the source
#           - 'start' (int): 1‑based line number of the `def` or `async def` header
#           - 'end' (int): 1‑based line number of the last line of the function body
#           - 'calls' (collection of str): every name that is the direct target of a
#             function‑call expression within the function body
#           - 'idents' (collection of str): every identifier whose value is read
#             within the function body
#           - 'body_words' (collection of str): every distinct alphabetic token of at
#             least 3 characters appearing in the function body source text, excluding
#             tokens inside comments, string literals, and the docstring
#           - 'exc_types' (collection of str): every exception type name that is
#             raised, caught, or bound within the function body
#           - 'docstring' (str): the docstring text of the function, or the empty
#             string when no docstring is present
#       * funcs_info includes both synchronous functions (FunctionDef) and
#         asynchronous functions (AsyncFunctionDef); the schema of entries is identical
#         regardless of the function kind.
#       * source_lines is a list[str] containing every line of the source file in
#         original order, with trailing newline characters removed
#       * classes is a list of dicts, one per class defined at module scope, each
#         containing the class name, 1‑based line range, method line numbers, and
#         per‑method entries following the same field schema as funcs_info entries
#   - If AST construction raises any exception (including SyntaxError, memory errors,
#     or IO errors during file read), returns (None, None, None).
#   - The function does not write to or rename any file; src_path is read only.
# [SPEC]

# [INFO]
# _collect_calls(node: ast.AST) -> collection[str]
#   Pre-condition: node is an AST node rooted at a function or method definition.
#   Post-condition: Returns every name that is the direct target of a function‑call
#     expression anywhere within the subtree rooted at node.
# [SPLIT]
# _collect_func_idents(node: ast.AST, source_lines: list[str]) -> tuple[collection[str], collection[str], collection[str]]
#   Pre-condition: node is an AST node rooted at a function or method definition.
#     source_lines is the list of source lines for the file containing node.
#   Post-condition: Returns a 3‑tuple (idents, body_words, exc_types) where:
#     - idents is every identifier whose value is read within the function body
#     - body_words is every distinct alphabetic token of at least 3 characters
#       extracted from the function body source text, excluding tokens inside
#       comments, string literals, and the docstring
#     - exc_types is every exception type name that is raised, caught, or bound
#       within the function body
# [SPLIT]
# _extract_classes(tree: ast.AST, source_lines: list[str]) -> list[dict]
#   Pre-condition: tree is a valid AST for a Python module. source_lines is the
#     corresponding source text as a list of lines.
#   Post-condition: Returns a list of dicts, one per class defined at module scope.
#     Each dict contains at minimum the class name, 1‑based line range, method line
#     numbers, and per‑method entries following the same field schema as funcs_info
#     entries.
# [INFO]

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
