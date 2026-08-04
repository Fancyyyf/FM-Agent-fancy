def _parse_issue_signals(issue_text: str) -> dict[str, set[str]]:
    """Extract multiple tiers of signals from the raw developer-intent text."""
    signals: dict[str, set[str]] = {
        'traceback_funcs': set(),
        'backtick_idents': set(),
        'dotted_refs':     set(),   # method names from Class.method refs
        'dotted_classes':  set(),   # class names from Class.method refs
        'plain_idents':    set(),
        'exception_types': set(),   # exception type names mentioned in the intent
        'all_words':       set(),
    }

    # T1: function names from Python tracebacks
    signals['traceback_funcs'] = set(re.findall(r'\bin (\w+)\s*\n', issue_text))

    # T2: identifiers inside backticks or fenced code blocks
    signals['backtick_idents'] = _extract_backtick_idents(issue_text)

    # T3: explicit Class.method dotted references
    for cls, meth in re.findall(r'\b([A-Z][a-zA-Z0-9]+)\.([a-z_][a-z0-9_]+)\b',
                                issue_text):
        signals['dotted_refs'].add(meth.lower())
        signals['dotted_classes'].add(cls.lower())
        # also add the method name parts
        for part in meth.lower().split('_'):
            if len(part) > 1:
                signals['dotted_refs'].add(part)

    # T4: CamelCase / snake_case words in prose
    for w in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:[A-Z_][a-zA-Z0-9_]+)+)\b',
                        issue_text):
        signals['plain_idents'].add(w.lower())
        for part in re.sub(r'([A-Z])', r'_\1', w).lower().strip('_').split('_'):
            if len(part) > 2:
                signals['plain_idents'].add(part)

    # T5: exception types  (e.g. AssertionError, ImportError)
    for exc in re.findall(r'\b([A-Z][a-zA-Z]+(?:Error|Exception|Warning))\b',
                          issue_text):
        signals['exception_types'].add(exc.lower())

    # T6: all alphabetic words ≥ 4 chars that aren't stop words
    for w in re.findall(r'\b([a-zA-Z]{4,})\b', issue_text.lower()):
        if w not in _STOP:
            signals['all_words'].add(w)

    return signals
