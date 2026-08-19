def _find_call_sites(text, lang_key, known_stems, keywords):
    """Find call sites in source text, returning set of matched stem names."""
    cleaned = _strip_comments_from_source(text, lang_key)
    regex = _get_call_regex(lang_key)
    found = set()
    for m in regex.finditer(cleaned):
        ident = m.group(1)
        if ident in keywords:
            continue
        if ident in known_stems:
            found.add(ident)
    return found
