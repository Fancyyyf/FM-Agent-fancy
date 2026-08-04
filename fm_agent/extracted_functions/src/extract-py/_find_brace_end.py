def _find_brace_end(lines, start_idx):
    """Find the line index of the closing '}' that matches the first '{' at or after start_idx.

    Handles string/char literals and // comments. Braces belonging to Go
    anonymous composite types (`interface{...}` / `struct{...}`, possibly
    spanning multiple lines) are tracked separately so they are not mistaken
    for the function body.

    Returns the line index of the closing brace, or len(lines)-1 if unmatched.
    """
    depth = 0
    found_open = False
    # Depth of braces inside an anonymous composite type; these do not count
    # toward the function body. `pending_type_brace` means an `interface`/
    # `struct` keyword was seen and its opening `{` is expected next.
    type_depth = 0
    pending_type_brace = False
    for i in range(start_idx, len(lines)):
        line = lines[i]
        j = 0
        while j < len(line):
            ch = line[j]
            # Skip string literals
            if ch == '"':
                j += 1
                while j < len(line):
                    if line[j] == '\\':
                        j += 2
                        continue
                    if line[j] == '"':
                        j += 1
                        break
                    j += 1
                continue
            # Skip char literals
            if ch == "'":
                j += 1
                while j < len(line):
                    if line[j] == '\\':
                        j += 2
                        continue
                    if line[j] == "'":
                        j += 1
                        break
                    j += 1
                continue
            # Line comment — skip rest
            if ch == '/' and j + 1 < len(line) and line[j + 1] == '/':
                break
            # Block comment
            if ch == '/' and j + 1 < len(line) and line[j + 1] == '*':
                j += 2
                while j < len(line):
                    if line[j] == '*' and j + 1 < len(line) and line[j + 1] == '/':
                        j += 2
                        break
                    j += 1
                # If block comment spans lines, continue on next line
                # (simplified: assume single-line block comments for now)
                continue
            # Inside an anonymous composite type: its braces belong to the type,
            # not the function body, so track them with a separate counter.
            if type_depth > 0:
                if ch == '{':
                    type_depth += 1
                elif ch == '}':
                    type_depth -= 1
                j += 1
                continue
            # A keyword's opening '{' is expected; consume whitespace until it.
            if pending_type_brace:
                if ch in ' \t':
                    j += 1
                    continue
                if ch == '{':
                    type_depth = 1
                    pending_type_brace = False
                    j += 1
                    continue
                # Not actually a composite type; fall through to normal handling.
                pending_type_brace = False
            # Detect Go anonymous composite types `interface{...}` / `struct{...}`,
            # whose braces (even when the type spans multiple lines) must not be
            # counted as the function body's braces.
            if ch in 'is' and (line.startswith('interface', j) or line.startswith('struct', j)):
                kw_len = 9 if line.startswith('interface', j) else 6
                end = j + kw_len
                prev_ok = j == 0 or not (line[j - 1].isalnum() or line[j - 1] == '_')
                next_ok = end >= len(line) or not (line[end].isalnum() or line[end] == '_')
                if prev_ok and next_ok:
                    k = end
                    while k < len(line) and line[k] in ' \t':
                        k += 1
                    if k < len(line) and line[k] == '{':
                        type_depth = 1
                        j = k + 1
                        continue
                    if k >= len(line):
                        # The opening '{' is on a following line.
                        pending_type_brace = True
                    j = end
                    continue
            if ch == '{':
                depth += 1
                found_open = True
            elif ch == '}':
                depth -= 1
                if found_open and depth == 0:
                    return i
            j += 1
    return len(lines) - 1
