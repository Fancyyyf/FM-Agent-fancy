def _analyze_project(proj_dir: str) -> ErlangAnalysis:
    root = os.path.abspath(proj_dir)
    fingerprint = _project_fingerprint(root)
    with _CACHE_LOCK:
        cached = _CACHE.get(root)
        if cached and cached[0] == fingerprint:
            return cached[1]

    analysis = _analyze_project_uncached(root)
    try:
        _persist_analysis(root, fingerprint, analysis)
    except OSError as exc:
        logging.warning("Unable to persist ELP Erlang call graph for %s: %s", root, exc)
    with _CACHE_LOCK:
        _CACHE[root] = (fingerprint, analysis)
    return analysis
