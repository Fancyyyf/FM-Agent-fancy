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
