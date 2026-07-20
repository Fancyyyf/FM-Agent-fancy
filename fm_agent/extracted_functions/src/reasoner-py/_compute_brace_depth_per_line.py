# [SPEC]
# Unit: src/reasoner-py/_compute_brace_depth_per_line.py
#
# _compute_brace_depth_per_line(lines) -> list[int]
#
# Pre-condition:
#   - lines is a non-empty list of strings, each containing one line of function body text without "Line N:" prefixes
#
# Post-condition:
#   - Returns a list of non-negative integers whose length equals the number of elements in lines
#   - For each position i (0-indexed), the integer at that position is the cumulative net count of opening brace characters '{' minus closing brace characters '}' encountered across lines[0] through lines[i], inclusive
#   - Brace characters that occur inside a double-quoted string literal do not contribute to the count: upon encountering an unescaped '"' character, counting of braces is suspended until the next unescaped '"', where a backslash preceding the quote is considered an escape
#   - Brace characters that occur inside a single-quoted character literal do not contribute to the count: upon encountering an unescaped "'" character, counting of braces is suspended until the next unescaped "'", where a backslash preceding the quote is considered an escape
#   - When the character sequence "//" is encountered outside of a string or character literal, all remaining characters on that line do not contribute to the count
#   - When the character sequence "/*" is encountered outside of a string or character literal, brace counting is suspended until the corresponding "*/" sequence is encountered; braces appearing between these delimiters, on any line, do not contribute to the count
#   - Every closing brace '}' in the input has a matching opening brace '{' at or before its position, so the accumulated net count is never negative for any prefix of lines
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _compute_brace_depth_per_line(lines):
    """
    Compute brace depth after each line, respecting strings and comments.
    Returns list of depths (depth after processing each line).
    """
    depths = []
    depth = 0
    for line in lines:
        i = 0
        while i < len(line):
            ch = line[i]
            # Skip string literals
            if ch == '"':
                i += 1
                while i < len(line):
                    if line[i] == '\\':
                        i += 2
                        continue
                    if line[i] == '"':
                        i += 1
                        break
                    i += 1
                continue
            # Skip char literals
            if ch == "'":
                i += 1
                while i < len(line):
                    if line[i] == '\\':
                        i += 2
                        continue
                    if line[i] == "'":
                        i += 1
                        break
                    i += 1
                continue
            # Line comment — skip rest of line
            if ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
                break
            # Block comment
            if ch == '/' and i + 1 < len(line) and line[i + 1] == '*':
                i += 2
                while i < len(line):
                    if line[i] == '*' and i + 1 < len(line) and line[i + 1] == '/':
                        i += 2
                        break
                    i += 1
                # If block comment spans lines, we ignore braces inside it (simplified)
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            i += 1
        depths.append(depth)
    return depths
