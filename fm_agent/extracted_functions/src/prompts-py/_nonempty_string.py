# [SPEC]
# Unit: src/prompts-py/_nonempty_string.py
#
# _nonempty_string(value)
#
# Pre-condition:
#   - (none)
#
# Post-condition:
#   - Returns True if and only if value is a string whose content, after removing leading and trailing whitespace, has length greater than zero
#   - Returns False for all other inputs (non-string types, empty strings, or strings consisting only of whitespace)
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

    def _nonempty_string(value):
        return isinstance(value, str) and bool(value.strip())
