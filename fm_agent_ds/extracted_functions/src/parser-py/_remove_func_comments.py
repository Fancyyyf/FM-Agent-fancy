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
