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
