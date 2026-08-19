def _has_terminating_statement(block, language):
    pattern = _TERMINATING_PATTERNS.get(language.lower())
    if not pattern:
        pattern = r'\b(return\b|exit\s*\(|raise\s|throw\s|abort\s*\()'
    return re.search(pattern, block) is not None
