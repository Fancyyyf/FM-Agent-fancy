def _strip_angle_brackets(text):
    """Remove balanced <...> segments from text (for template parameters)."""
    result = []
    depth = 0
    for ch in text:
        if ch == '<':
            depth += 1
        elif ch == '>':
            if depth > 0:
                depth -= 1
        else:
            if depth == 0:
                result.append(ch)
    return ''.join(result)
