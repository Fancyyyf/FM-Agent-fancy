# [SPEC]
# Unit: src/scope-py/_collect_calls.py
#
# _collect_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]
#
# Pre-condition:
#   - node is an AST node, typically a FunctionDef or AsyncFunctionDef
#
# Post-condition:
#   - Returns a set of zero or more strings, each being the name used as the
#     direct target of a function-call expression (ast.Call) at any depth
#     within the AST subtree rooted at node
#   - For a call expression whose target is an ast.Name, the identifier
#     string (the ast.Name.id attribute) is included in the result set
#   - For a call expression whose target is an ast.Attribute, the attribute
#     name (the ast.Attribute.attr string) is included in the result set;
#     the receiver sub-expression is not traversed for additional call-target
#     names
#   - For a call expression whose target is any other AST node kind
#     (including but not limited to ast.Subscript, ast.Lambda, ast.Call), no
#     name is collected from that call expression
#   - The returned set contains no duplicate entries: each distinct
#     call-target name string appears at most once
#   - If the subtree contains no ast.Call nodes, returns an empty set
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _collect_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    calls: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                calls.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                calls.add(n.func.attr)
    return calls
