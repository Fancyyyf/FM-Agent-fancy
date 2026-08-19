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
