# [SPEC]
# Unit: src/languages/erlang-py/_function_id.py
#
# _escape_component(value: str) -> str
#
# Pre-condition:
#   - value is a string
#
# Post-condition:
#   - Returns an escaped representation of value suitable for use as a component in a fully-qualified name (FQN) where double-underscore ("__") serves as the component separator
#   - The returned string contains no occurrence of the substring "__"
#   - When value is non-empty, the returned string is non-empty
#   - Each character of value that is an ASCII alphanumeric or underscore is preserved as-is at its original position
#   - Every other character is replaced by an underscore followed by the lowercase hexadecimal representation of its Unicode code point (zero-padded to at least 2 digits), preserving the original relative order of all characters
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _escape_component(value: str) -> str:
    result = []
    for char in value:
        if char.isascii() and (char.isalnum() or char == "_"):
            result.append(char)
        else:
            result.append(f"_{ord(char):02x}")
    return "".join(result)
