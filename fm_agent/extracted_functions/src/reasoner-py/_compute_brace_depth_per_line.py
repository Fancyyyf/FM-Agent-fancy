# [SPEC]
# Unit: src/reasoner-py/_compute_brace_depth_per_line.py
#
# _compute_brace_depth_per_line(lines) -> list[int]
#
# Pre-condition:
#   - lines is a non-empty list of strings, each containing one line of function body text without "Line N:" prefixes
#   - The input represents a function body with balanced braces, i.e., every '}' has a matching '{' earlier in the sequence, so the cumulative depth never becomes negative.
#
# Post-condition:
#   - Returns a list of integers whose length equals len(lines)
#   - For each index i, the integer is the cumulative net count of '{' minus '}' characters encountered across lines[0] through lines[i], inclusive, after applying the following exclusion rules:
#       * Characters inside a double-quoted string literal (delimited by unescaped '"', where backslash escapes the next character) are excluded.
#       * Characters inside a single-quoted character literal (delimited by unescaped "'", with backslash escape) are excluded.
#       * From the point where the sequence "//" occurs outside any literal, all remaining characters on that line are excluded.
#       * From the point where the sequence "/*" occurs outside any literal, all remaining characters on that line are excluded (the simplified implementation does not propagate the block comment into subsequent lines).
#   - Because of the balanced-brace precondition, each returned integer is non-negative.
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
