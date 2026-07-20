# [SPEC]
# Unit: src/generate_batch_prompts-py/_info_line_mentions_name.py
#
# _info_line_mentions_name(first_line: str, name: str) -> bool
#
# Pre-condition:
#   - first_line is a string
#   - name is a string
#
# Post-condition:
#   - Returns False when name is empty
#   - When name contains the substring "::", returns True if and only if name
#     appears as a substring anywhere in first_line
#   - When name does NOT contain "::", returns True if and only if name appears
#     in first_line at a position not immediately preceded by an ASCII letter,
#     digit, or underscore, and immediately followed by either an opening
#     parenthesis (with optional whitespace between name and parenthesis) or a
#     non-word-character position (including end-of-string)
#   - The return value depends solely on first_line and name; the function is
#     pure (no side effects) and deterministic
# [SPEC]

# [INFO]
# re.search(pattern: str, string: str, flags: int = 0) -> Match | None
#   Pre-condition: pattern is a string interpreted as a regular expression;
#     string is the text to search within
#   Post-condition: returns a Match object representing the first location where
#     pattern successfully matches within string; returns None when pattern does
#     not match at any position in string
# [INFO]

def _info_line_mentions_name(first_line: str, name: str) -> bool:
    if not name:
        return False
    if "::" in name:
        return name in first_line
    return bool(re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?:\s*\(|\b)", first_line))
