# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_extract_classes.py
#
# _extract_classes(tree: ast.Module, source_lines: list[str]) -> list[dict]
#
# Pre-condition:
#   - tree is a valid AST for a Python module, produced by ast.parse without raising
#     an exception.
#   - source_lines is a list[str] containing every line of the source file that
#     produced tree, in original order, with trailing newlines removed.
#
# Post-condition:
#   - Returns a list of dicts, one per class defined at module scope in tree.
#   - The list is ordered by ascending class start line (1‑based lineno).
#   - Each dict contains at minimum these keys:
#       * 'name' (str): the class name as written in the source code.
#       * 'lineno' (int): the 1‑based line number of the class definition header.
#       * 'end_lineno' (int): the 1‑based line number of the last line of the class
#         body.
#       * 'docstring' (str): the docstring text of the class, or the empty string
#         when no docstring is present.
#       * 'method_linenos' (list[int]): the 1‑based line numbers of every method
#         (FunctionDef or AsyncFunctionDef) defined directly within the class body,
#         sorted in ascending order.
#   - Each dict also contains per‑method detail entries following the same field
#     schema as funcs_info entries. Every method defined within the class is described
#     by a sub‑dict with keys: 'name' (str), 'start' (int), 'end' (int), 'calls'
#     (collection of str), 'idents' (collection of str), 'body_words' (collection of
#     str), 'exc_types' (collection of str), and 'docstring' (str).
#   - If tree contains no class definitions at module scope, returns an empty list.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
