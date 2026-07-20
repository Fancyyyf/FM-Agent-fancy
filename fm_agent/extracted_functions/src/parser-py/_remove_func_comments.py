# [SPEC]
# Unit: src/parser-py/_remove_func_comments.py
#
# _remove_func_comments(code: str) -> str
#
# Pre-condition:
#   - code is a string of arbitrary content, typically source code that may contain
#     comments and string literals
#
# Post-condition:
#   - Returns a copy of code with all comments removed and all string literal
#     content preserved exactly as in the input
#   - Comments removed are: block comments delimited by /* and */, line comments
#     starting with //, and # comments that appear after at least one non-whitespace
#     character on the same line
#   - A # character that is the first non-whitespace character on a line is NOT
#     treated as a comment start and is preserved in the output
#   - Within string literals delimited by " or ', no character is interpreted as
#     comment syntax; all characters within string literals are preserved verbatim,
#     including backslash-escaped characters
#   - Lines that contain only whitespace after comment removal are omitted from
#     the output
#   - The relative order of all preserved characters, including newlines, is
#     unchanged from the input
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _remove_func_comments(code):
    result = []
    index = 0
    in_block_comment = False
    in_string = False
    string_delimiter = ""
    line_start = True

    while index < len(code):
        char = code[index]
        next_char = code[index + 1] if index + 1 < len(code) else ""

        if in_block_comment:
            if char == '*' and next_char == '/':
                in_block_comment = False
                index += 2
                continue
            if char == '\n':
                result.append(char)
                line_start = True
            index += 1
            continue

        if in_string:
            result.append(char)
            if char == '\\' and index + 1 < len(code):
                result.append(code[index + 1])
                index += 2
                continue
            if char == string_delimiter:
                in_string = False
            line_start = char == '\n'
            index += 1
            continue

        if char in ('"', "'"):
            in_string = True
            string_delimiter = char
            result.append(char)
            line_start = False
            index += 1
            continue

        if char == '/' and next_char == '*':
            in_block_comment = True
            index += 2
            continue

        if char == '/' and next_char == '/':
            index += 2
            while index < len(code) and code[index] != '\n':
                index += 1
            continue

        if char == '#' and not line_start:
            while index < len(code) and code[index] != '\n':
                index += 1
            continue

        result.append(char)
        if char == '\n':
            line_start = True
        elif not char.isspace():
            line_start = False
        index += 1

    cleaned_lines = [line for line in ''.join(result).split('\n') if line.strip()]
    return '\n'.join(cleaned_lines)
