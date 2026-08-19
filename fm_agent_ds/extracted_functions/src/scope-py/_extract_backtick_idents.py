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
