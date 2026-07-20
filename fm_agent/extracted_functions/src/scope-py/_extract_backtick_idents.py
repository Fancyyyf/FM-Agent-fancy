# [SPEC]
# Unit: src/scope-py/_extract_backtick_idents.py
#
# _extract_backtick_idents(issue_text: str) -> set[str]
#
# Pre-condition:
#   - issue_text is a string
#
# Post-condition:
#   - Returns a set of lowercased identifier strings extracted from issue_text
#   - Every returned string has length ≥ 2 and consists of ASCII letters, digits, and underscores
#   - An identifier is included if and only if it appears within a backtick-quoted span (`` `...` ``) or a triple-backtick-fenced code block (`` ```...``` ``) in issue_text
#   - Identifiers that match Python language keywords or a fixed set of common built-in / stop-word names are excluded from the returned set
#   - For backtick-quoted spans, leading RST/Sphinx role prefixes of the form `<word>:<word>` are stripped before identifier extraction; the prefix portion contributes no identifiers to the result
#   - Within code blocks, only identifiers of length ≥ 3 characters are extracted
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extract_backtick_idents(issue_text: str) -> set[str]:
    """Extract meaningful identifiers from backtick spans and code blocks.

    Filters out Python keywords, common builtins, and RST/Sphinx role prefixes
    (e.g. ``py:class`` → keep nothing; ``Literal`` → keep 'literal').
    """
    result: set[str] = set()

    def _add(token: str) -> None:
        t = token.lower().strip('_')
        if len(t) >= 2 and t not in _PY_KEYWORDS and t not in _STOP:
            result.add(t)

    for raw in re.findall(r'`([^`]+)`', issue_text):
        # Strip RST/Sphinx role prefix (e.g. "py:class", "ref:", "meth:")
        raw = re.sub(r'^[a-z]+:[a-z]+\s*', '', raw.strip())
        for part in re.findall(r'[a-zA-Z_][a-zA-Z0-9_]{1,}', raw):
            _add(part)

    for block in re.findall(r'```.*?```', issue_text, re.DOTALL):
        for ident in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', block):
            _add(ident)

    return result
