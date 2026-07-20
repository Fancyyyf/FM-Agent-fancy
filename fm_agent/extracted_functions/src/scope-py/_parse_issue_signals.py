# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_parse_issue_signals.py
#
# _parse_issue_signals(issue_text: str) -> dict[str, set[str]]
#
# Pre-condition:
#   - issue_text is a string containing developer-intent prose, which may include
#     Python traceback lines, backtick-quoted identifiers, Class.method references,
#     CamelCase and snake_case names, exception type names, and free-form text.
#
# Post-condition:
#   - Returns a dict with exactly seven keys, each mapping to a set of lowercased strings:
#       'traceback_funcs', 'backtick_idents', 'dotted_refs', 'dotted_classes',
#       'plain_idents', 'exception_types', 'all_words'.
#   - Every element of every set originates from a substring of issue_text and is lowercased.
#   - 'traceback_funcs': the set of function names appearing immediately after an
#     "  in " prefix at the end of a line, as found in Python traceback entries.
#   - 'backtick_idents': the set of identifiers extracted from backtick-quoted spans
#     and triple-backtick-fenced code blocks anywhere in issue_text.
#   - 'dotted_refs': the set of method-name words from Class.method patterns, plus
#     every underscore-delimited subpart of each such method name whose length
#     exceeds 1 character.
#   - 'dotted_classes': the set of class-name words from Class.method patterns.
#   - 'plain_idents': the set of words matching CamelCase or snake_case identifier
#     patterns, plus every subpart derived by splitting such identifiers whose
#     length exceeds 2 characters.
#   - 'exception_types': the set of words matching a PascalCase pattern whose suffix
#     is exactly "Error", "Exception", or "Warning".
#   - 'all_words': the set of every alphabetic word of length ≥ 4 characters that
#     is not a member of the stop-word set.
# [SPEC]

# [INFO]
# _extract_backtick_idents(issue_text: str) -> set[str]
#   Pre-condition: issue_text is a string.
#   Post-condition: Returns a set of lowercased identifier strings extracted from
#     backtick-quoted spans and triple-backtick-fenced code blocks in issue_text.
# [INFO]

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
