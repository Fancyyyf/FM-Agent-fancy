# [SPEC]
# Unit: src/parser-py/_strip_section_comment_prefix.py
#
# _strip_section_comment_prefix(line: str) -> str
#
# Pre-condition:
#   - line is a string
#
# Post-condition:
#   - Returns a string where any leading comment prefix at the start of the line
#     (after optional leading whitespace) has been removed
#   - A recognized comment prefix is one of:
#       * two or more consecutive `/` characters,
#       * two or more consecutive `-` characters,
#       * one or more consecutive `#` characters, or
#       * one or more consecutive `%` characters
#     optionally followed by a single whitespace character.
#   - Leading whitespace characters that precede the comment prefix are preserved
#     unchanged in the returned string
#   - When the line does not begin with (optional leading whitespace followed by)
#     a recognized comment prefix, the line is returned unchanged
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _strip_section_comment_prefix(line):
    return re.sub(r'^(\s*)(?://+|#+|--+|%+)\s?', r'\1', line)
