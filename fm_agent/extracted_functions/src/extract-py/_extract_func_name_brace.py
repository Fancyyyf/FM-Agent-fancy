# [SPEC]
# Unit: src/extract.py
#
# _extract_func_name_brace(signature_text, lang_cfg) -> str | None
#
# Pre-condition:
#   - signature_text is a string containing one or more concatenated source lines forming a function signature in a brace-delimited language
#   - lang_cfg is a language configuration entry with a "keywords" key whose value is a set of language reserved words
#
# Post-condition:
#   - Returns the function name as a string when signature_text contains a recognized function-definition pattern and the identified name is not a language keyword; returns None otherwise
#   - For languages that support operator overloading, an operator definition signature (e.g., one containing `operator()`, `operator[]`, or an operator symbol following the `operator` keyword) is recognized and the full operator token is returned as the function name
#   - For other function-definition forms, returns the first non-keyword identifier that immediately precedes an opening parenthesis, after template angle-bracket content (i.e., text between `<` and matching `>`) has been removed from the signature text
#   - The returned name does not include any tokens of lang_cfg["keywords"]
# [SPEC]

# [INFO]
# _strip_angle_brackets(text: str) -> str
#   Pre-condition: text is a string that may contain angle-bracket-delimited sections
#   Post-condition: Returns text with all content enclosed in matching angle brackets removed; characters outside angle brackets are preserved in their original order
# [INFO]

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
