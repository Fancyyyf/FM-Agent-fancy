# [SPEC]
# Unit: src/generate_topdown_layers-py/_find_call_sites.py
#
# _find_call_sites(text, lang_key, known_stems, keywords) -> set[str]
#
# Pre-condition:
#   - text is a string containing source code text
#   - lang_key is a recognized language key string
#   - known_stems is a non-empty set of function-name stem strings
#   - keywords is a set of keyword strings to exclude from results
#
# Post-condition:
#   - Returns the subset of known_stems that appear as bare-name call sites in
#     text, excluding any identifier that is also in keywords
#   - An identifier in known_stems is included in the result if and only if it
#     appears as a call site in the source text after comment removal AND is not
#     in the keywords set
#   - Identifiers within comment regions (delimited per the lang_key language's
#     comment syntax) are not treated as call sites
#   - Identifiers within string or character literal contexts for the given
#     language are not treated as call sites
#   - The returned set is always a subset of known_stems and is disjoint from
#     keywords
#   - The return value is deterministic for a given (text, lang_key, known_stems,
#     keywords) input
# [SPEC]

# [INFO]
# _strip_comments_from_source(text, lang_key) -> str
#   Pre-condition: text is a string containing source code (may be empty); lang_key is a string identifying a programming language
#   Post-condition: returns a string of the same length as text, where characters inside comments and string literals are replaced by spaces (newlines within comments are preserved); all other characters remain unchanged
# [SPLIT]
# _get_call_regex(lang_key) -> Pattern
#   Pre-condition: lang_key is a recognized language key
#   Post-condition: returns a compiled regex pattern whose matches identify
#     bare-name function-call identifiers in the given language; capture group 1
#     yields the matched identifier string
# [INFO]

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
