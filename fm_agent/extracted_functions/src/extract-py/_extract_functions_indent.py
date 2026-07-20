# [SPEC]
# Unit: src/extract-py/_extract_functions_indent.py
#
# _extract_functions_indent(lines, lang_cfg) -> [(str, int, int)]
#
# Pre-condition:
#   - lines is a list of strings representing source code lines with trailing
#     whitespace stripped
#   - lang_cfg is a LANG_CONFIG entry whose body type is "indent"
#
# Post-condition:
#   - Returns a list of (raw_name, start, end) tuples, ordered by ascending
#     start index
#   - Each tuple identifies one function definition found in lines:
#     * raw_name is the function identifier extracted from the definition line
#     * start is the zero-based index of the block's first line: either the
#       definition line itself, or the earliest immediately-preceding decorator
#       line when the definition line is preceded by one or more consecutive
#       decorator lines
#     * end is the zero-based index of the last non-blank line in the function
#       body
#   - The contiguous span lines[start..end] contains exactly one function
#     definition header; every non-blank line in that span either belongs to
#     the function body (indented more deeply than the definition header) or
#     forms a continuation of the header at the same indentation level
#   - Lines whose indentation is shallower than or equal to the definition
#     header, that are not header continuations, are classified as belonging
#     to a subsequent top-level construct and are excluded from the span
#   - Blank lines within the span do not affect boundary detection
#   - Trailing blank lines after the last non-blank body line are excluded
#     from the span (end is reduced to the last non-blank line)
#   - Returns an empty list when no line in the input matches the
#     function-definition pattern for the language
#   - Function names are returned as raw identifiers extracted directly from
#     the definition line; deduplication of duplicate names is the caller's
#     responsibility
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extract_functions_indent(lines, lang_cfg):
    """Extract functions from an indent-delimited language (Python)."""
    functions = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Look for 'def ' at any indentation level
        m = re.match(r'^(\s*)def\s+(\w+)\s*\(', line)
        if not m:
            i += 1
            continue

        indent = len(m.group(1))
        name = m.group(2)
        func_start = i

        # Handle decorators — walk backwards to include them
        while func_start > 0 and lines[func_start - 1].strip().startswith('@'):
            func_start -= 1

        # Find end of function body: subsequent lines with greater indentation
        # (or blank lines interspersed)
        j = i + 1
        while j < len(lines):
            l = lines[j]
            if l.strip() == '':
                j += 1
                continue
            line_indent = len(l) - len(l.lstrip())
            if line_indent == indent and re.match(r'\)\s*(:|->)', l.lstrip()):
                j += 1
                continue
            if line_indent <= indent:
                break
            j += 1

        # j is now the first line after the function body
        func_end = j - 1
        # Trim trailing blank lines
        while func_end > i and lines[func_end].strip() == '':
            func_end -= 1

        functions.append((name, func_start, func_end))
        i = j

    return functions
