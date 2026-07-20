# [SPEC]
# Unit: src/extract.py
#
# _strip_angle_brackets(text: str) -> str
#
# Pre-condition:
#   - text is a string
#
# Post-condition:
#   - Returns text with all content enclosed within matching angle-bracket pairs removed
#   - Angle-bracket pairs are matched using balanced counting: each '<' opens a new scope, each '>' closes the most recently opened scope
#   - All characters between a matching '<' and '>' (the brackets themselves and everything between them) are omitted from the result
#   - Characters not inside any matching pair appear in the result in their original relative order
#   - A '>' with no preceding unmatched '<' is not inside any matching pair and appears in the result
#   - If the input contains no '<' characters, every character in the input appears in the result in original order
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
