# [SPEC]
# Unit: src/prompts.py
#
# _nonempty_string(value) -> bool
#
# Pre-condition:
#   - (no requirements)
#
# Post-condition:
#   - Returns True when value is a string and, after removing all leading and trailing whitespace characters, the resulting string is non-empty
#   - Returns False otherwise, including when value is not a string or when it is a string that consists solely of whitespace characters or is empty
# [SPEC]

    def _nonempty_string(value):
        return isinstance(value, str) and bool(value.strip())
