def _extract_func_name_brace(signature_text, lang_cfg):
    """Extract the function name from a brace-delimited language signature."""
    lang_keywords = lang_cfg["keywords"]

    m = re.search(
        r'\b(operator\s*(?:\[\]|\(\)|[+\-*/%&|^~!=<>]+|new(?:\s*\[\s*\])?|delete(?:\s*\[\s*\])?))'
        r'\s*\(',
        signature_text,
    )
    if m:
        return m.group(1)

    cleaned = _strip_angle_brackets(signature_text)
    for m in re.finditer(r'\b(\w+)\s*\(', cleaned):
        name = m.group(1)
        if name not in lang_keywords:
            return name
    return None
