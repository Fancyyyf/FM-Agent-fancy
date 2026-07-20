# [SPEC]
# Unit: src/parser-py/_extract_function_name.py
#
# _extract_function_name(signature_line: str) -> str | None
#
# Pre-condition:
#   - signature_line is a string
#
# Post-condition:
#   - Returns the function name extracted from the signature line; returns None if
#     no recognizable function name is found
#   - A function name is recognizable when signature_line contains an identifier
#     (starting with an alphabetic character or underscore, followed by zero or more
#     alphanumeric characters or underscores) immediately followed by optional
#     whitespace and an opening parenthesis `(`
#   - When multiple such patterns exist in signature_line, the first (leftmost) match
#     determines the returned function name
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extract_function_name(signature_line):
    match = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(', signature_line)
    return match.group(1) if match else None
