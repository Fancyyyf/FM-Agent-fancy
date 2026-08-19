def _extract_functions_brace(lines, lang_key, lang_cfg):
    """Extract functions from a brace-delimited language source."""
    functions = []
    i = 0
    skip_prefixes = lang_cfg["skip_prefixes"]
    skip_kw_line = lang_cfg["skip_keywords_line"]
    in_block_comment = False
    _block_comment_langs = {"cpp", "c", "cuda", "java", "javascript", "typescript", "arkts"}

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()

        # Skip blank lines
        if not stripped:
            i += 1
            continue

        # Skip /* */ block comments for C-family languages
        if lang_key in _block_comment_langs:
            if in_block_comment:
                end_idx = stripped.find("*/")
                if end_idx != -1:
                    in_block_comment = False
                i += 1
                continue
            start_idx = stripped.find("/*")
            if start_idx != -1:
                # Check whether the block comment closes on the same line
                after_start = stripped[start_idx + 2:]
                if "*/" not in after_start:
                    in_block_comment = True
                i += 1
                continue

        # Skip comment / preprocessor / using lines
        if any(stripped.startswith(p) for p in skip_prefixes):
            i += 1
            continue

        # Handle anonymous namespace (C++)
        if lang_key in ("cpp", "c") and re.match(r'^namespace\s*\{', stripped):
            # Descend into anonymous namespace — skip the opening line
            i += 1
            continue

        # Handle named namespace — skip entire block
        if lang_key in ("cpp", "c") and re.match(r'^namespace\s+\w', stripped):
            # Find the opening brace and skip to the matching close
            # But we actually want to scan inside named namespaces too for
            # functions. Let's just skip the namespace line and descend.
            if '{' in stripped:
                i += 1
                continue
            else:
                # Multi-line namespace declaration — skip until {
                j = i + 1
                while j < len(lines) and '{' not in lines[j]:
                    j += 1
                i = j + 1
                continue

        # Skip lines starting with class/struct/etc. keywords
        if any(stripped.startswith(kw) for kw in skip_kw_line):
            # But if it's a method definition (has '(' and '{'), still skip
            i += 1
            continue

        # Skip constexpr variable declarations (C++)
        if lang_key in ("cpp", "c") and stripped.startswith("constexpr") and stripped.endswith(";"):
            i += 1
            continue

        # Go: detect func keyword
        if lang_key == "go":
            if not stripped.startswith("func ") and not stripped.startswith("func("):
                i += 1
                continue
            # Extract name
            m = re.search(r'func\s+(?:\([^)]*\)\s*)?(\w+)', stripped)
            if not m:
                i += 1
                continue
            name = m.group(1)
            # Find opening brace
            sig_lines = [lines[i]]
            sig_end = i
            for look in range(i, min(i + 10, len(lines))):
                if '{' in lines[look]:
                    sig_end = look
                    sig_lines = lines[i:look + 1]
                    break
            end = _find_brace_end(lines, sig_end)
            functions.append((name, i, end))
            i = end + 1
            continue

        # Rust: detect fn keyword
        if lang_key == "rust":
            m = re.match(
                r'(?:pub(?:\s*\([^)]*\))?\s+)?'   # pub, pub(crate), pub(super), pub(in ...)
                r'(?:default\s+)?'
                r'(?:const\s+)?'
                r'(?:async\s+)?'
                r'(?:unsafe\s+)?'
                r'(?:extern\s+"[^"]*"\s+)?'
                r'fn\s+(\w+)',
                stripped,
            )
            if not m:
                i += 1
                continue
            # Skip functions annotated with #[test].
            # Walk backward through the contiguous run of attribute/blank lines
            # that immediately precede this fn — stop at the first line that is
            # neither blank nor an attribute (#[...]) so we never reach a #[test]
            # that belonged to a different, already-processed function.
            j = i - 1
            has_test_attr = False
            while j >= 0:
                prev = lines[j].strip()
                if prev == '' or re.match(r'^#\[', prev) or prev.startswith('//'):
                    if prev == '#[test]':
                        has_test_attr = True
                        break
                    j -= 1
                else:
                    break
            if has_test_attr:
                sig_end = i
                for look in range(i, min(i + 10, len(lines))):
                    if '{' in lines[look]:
                        sig_end = look
                        break
                i = _find_brace_end(lines, sig_end) + 1
                continue
            name = m.group(1)
            sig_end = i
            for look in range(i, min(i + 10, len(lines))):
                if '{' in lines[look]:
                    sig_end = look
                    break
            end = _find_brace_end(lines, sig_end)
            functions.append((name, i, end))
            i = end + 1
            continue

        # For C/C++/Java/JS/TS: candidate line has '(' and does not end with ';'
        # Must not be indented (column 0) for C/C++; for Java/JS/TS allow indentation
        if lang_key in ("cpp", "c"):
            if line[0:1].isspace():
                i += 1
                continue

        if '(' not in stripped or stripped.rstrip().endswith(';'):
            i += 1
            continue

        # Collect signature lines up to opening brace
        sig_start = i
        sig_end = i
        sig_text = stripped
        for look in range(i, min(i + 6, len(lines))):
            if '{' in lines[look]:
                sig_end = look
                sig_text = ' '.join(lines[sig_start:look + 1])
                break

        if '{' not in lines[sig_end]:
            i += 1
            continue

        # JS/TS: also handle `function name(` syntax
        if lang_key in ("javascript", "typescript", "arkts"):
            m = re.search(r'\bfunction\s+(\w+)', sig_text)
            if m:
                name = m.group(1)
            else:
                name = _extract_func_name_brace(sig_text, lang_cfg)
        else:
            name = _extract_func_name_brace(sig_text, lang_cfg)

        if not name:
            i += 1
            continue

        end = _find_brace_end(lines, sig_end)
        functions.append((name, sig_start, end))
        i = end + 1

    return functions
