# [SPEC]
# Unit: src/parser-py/parse_input_function.py
#
# parse_input_function(file_path: str) -> (str, str, FunctionSpecMap)
#
# Pre-condition:
#   - file_path points to a file that exists and is readable as UTF-8 text
#   - The file MAY contain a [SPEC] section: two lines whose stripped text is "# [SPEC]

# [INFO]
,
#     with callee specification entries between them separated by "# [SPLIT]" markers
#   - The remainder of the file after the closing [INFO] or [SPEC] marker (or the entire
#     file content when neither marker is found) contains Python source code
#
# Post-condition:
#   - Returns a 3-tuple (func, nl_spec, knowledge)
#   - func: a string of the source code body — all comment lines (lines where the first
#     non-whitespace character is '#') are removed, and each remaining line is prefixed
#     with "Line {N}: " where N is the 1-based line number in the comment-stripped text
#   - nl_spec: the text between the opening and closing [SPEC] markers (empty string ""
#     when no [SPEC] section is present)
#   - knowledge: a FunctionSpecMap built from the [INFO] section's callee entries,
#     where each callee name maps to its spec text and the .signatures dict maps callee
#     names to their signature lines; empty FunctionSpecMap when no [INFO] section exists
#   - The source code body is taken from the portion of the file after the closing [INFO]
#     marker when an [INFO] section exists, otherwise after the closing [SPEC] marker when
#     a [SPEC] section exists, otherwise from the entire file content
# [SPEC]
# [INFO]

def parse_input_function(file_path):
    """
    Parse a file with three parts:
    1. func: remaining lines after the closing [INFO] block, with comments removed
    2. nl_spec: lines between two standalone [SPEC] marker lines
    3. knowledge: a map from function name to spec parsed from the [INFO] block
    
    Returns:
        tuple: (func, nl_spec, knowledge)
    """
    with open(file_path, 'r') as file:
        content = file.read()

    lines = content.splitlines()

    nl_spec, _, spec_end_idx = _extract_marked_section(lines, "SPEC")
    knowledge_text, _, info_end_idx = _extract_marked_section(lines, "INFO")
    knowledge = _parse_info_section(knowledge_text)

    # func: after the closing [INFO] marker if present, else after [SPEC], else all
    func = ""
    if info_end_idx is not None:
        func = '\n'.join(lines[info_end_idx + 1:]).lstrip('\n')
    elif spec_end_idx is not None:
        func = '\n'.join(lines[spec_end_idx + 1:]).lstrip('\n')
    else:
        func = content

    func = _remove_func_comments(func)

    # Add line numbers to each line in func
    func_lines = func.split('\n')
    numbered_lines = [f"Line {i+1}: {line}" for i, line in enumerate(func_lines)]
    func = '\n'.join(numbered_lines)

    return func, nl_spec, knowledge
