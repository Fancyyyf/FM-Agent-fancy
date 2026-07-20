# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_generic_func_info.py
#
# _generic_func_info(name: str, start0: int, end0: int,
#                    source_lines: list[str], lang_cfg: dict) -> dict
#
# Pre-condition:
#   - name is a non-empty string; the function name
#   - start0 and end0 are 0-based line indices with start0 ≤ end0
#   - source_lines is a list[str] of the source file text, with
#     len(source_lines) > end0
#   - lang_cfg is a dict containing a 'keywords' key whose value is
#     a set[str] of language reserved words
#
# Post-condition:
#   - Returns a dict containing the canonical metadata and signal fields
#     for one function extracted from a generic (non-Python) source file
#   - The returned dict has exactly the following keys, all present:
#     * 'name': str — equal to the input name parameter
#     * 'start': int — equals start0 + 1 (1-based inclusive start line)
#     * 'end': int — equals end0 + 1 (1-based inclusive end line)
#     * 'calls': set[str] — names of functions called within the body,
#       case-preserved, excluding names present in lang_cfg['keywords']
#     * 'idents': set[str] — lowercased identifier-like tokens extracted
#       from the body
#     * 'body_words': set[str] — lowercased alphabetic words of length
#       ≥ 4 from the body, excluding common stop words
#     * 'exc_types': set[str] — lowercased exception-type names extracted
#       from the body
#     * 'docstring': str — always the empty string ''
#   - All token-extraction fields are scoped exclusively to the
#     concatenation of source_lines[start0] through source_lines[end0]
#     (inclusive)
#   - Each set-valued field is empty when no tokens of that category are
#     found in the body
#   - The returned dict is deterministic for a given input
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _generic_func_info(name: str, start0: int, end0: int,
                       source_lines: list[str], lang_cfg: dict) -> dict:
    """
    Build a funcs_info dict for one function in a non-Python (or AST-fallback) source.

    start0/end0 are 0-based inclusive line indices as returned by the extract.py
    brace/indent extractors. The 'start'/'end' fields are stored 1-based to match the AST
    convention used throughout scope.py (source_lines[start - 1] is the signature line).
    Identifiers, calls and exception types are recovered by regex over the function body.
    """
    body_text = '\n'.join(source_lines[start0:end0 + 1])
    keywords = lang_cfg.get('keywords', set())

    idents = {t.lower() for t in _IDENT_RE.findall(body_text)}
    body_words = {w for w in re.findall(r'\b([a-zA-Z]{4,})\b', body_text.lower())
                  if w not in _STOP}
    exc_types = {e.lower() for e in _EXC_TOKEN_RE.findall(body_text)}
    # Keep call names in their original case so call-graph propagation can match them
    # against function names (which preserve case), excluding language control keywords.
    calls = {m for m in _CALL_RE.findall(body_text) if m not in keywords}

    return {
        'name':       name,
        'start':      start0 + 1,
        'end':        end0 + 1,
        'calls':      calls,
        'idents':     idents,
        'body_words': body_words,
        'exc_types':  exc_types,
        'docstring':  '',
    }
