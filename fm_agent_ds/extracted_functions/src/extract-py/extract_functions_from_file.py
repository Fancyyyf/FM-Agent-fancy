def extract_functions_from_file(filepath, lang_key):
    """Extract all functions from a single source file.

    Returns a list of (function_name, source_text) tuples.
    """
    lang_cfg = LANG_CONFIG[lang_key]

    with open(filepath, 'r', errors='replace') as f:
        lines = f.readlines()

    # Normalize line endings
    lines = [l.rstrip('\n').rstrip('\r') for l in lines]

    if lang_cfg["body"] == "brace":
        raw_funcs = _extract_functions_brace(lines, lang_key, lang_cfg)
    elif lang_cfg["body"] == "indent":
        raw_funcs = _extract_functions_indent(lines, lang_cfg)
    else:
        # Semantic-only languages (currently Erlang) are extracted by their
        # registered backend and have no reliable file-local fallback.
        return []

    # Deduplicate names (applied after canonicalize so operator overloads
    # produce safe filenames and FQN components).
    name_counts = {}
    results = []
    for name, start, end in raw_funcs:
        cname = canonicalize(name)
        count = name_counts.get(cname, 0)
        name_counts[cname] = count + 1
        if count > 0:
            deduped = f"{cname}_{count}"
        else:
            deduped = cname
        source = '\n'.join(lines[start:end + 1]) + '\n'
        results.append((deduped, source))

    return results
