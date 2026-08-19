def call_edges_all(proj_dir: str, lang_keys) -> tuple:
    """Call call_edges for each language in lang_keys and merge results.

    Returns (edges, langs) where edges is {caller_fqn: {callee_fqns}} and langs is
    the set of language keys codegraph handled (it returned a dict, even if empty
    — None means the backend was unavailable and the caller should use regex).
    """
    edges = {}
    langs = set()
    for lang in lang_keys:
        if lang not in REGISTRY:
            continue
        result = REGISTRY[lang].call_edges(proj_dir)
        # A handler returns None when its backend (codegraph) is unavailable, and
        # a dict (possibly empty) when it handled the language. Treat "handled but
        # no edges" as codegraph-authoritative — add the language to `langs` so the
        # caller uses the codegraph path — instead of falling back to regex, which
        # would otherwise invent edges (e.g. match a function's own signature) for
        # a genuinely call-free project.
        if result is not None:
            langs.add(lang)
            for key, callees in result.items():
                edges.setdefault(key, set()).update(callees)
    return edges, langs
