def _analysis_or_empty(proj_dir: str) -> ErlangAnalysis:
    try:
        return _analyze_project(proj_dir)
    except Exception as exc:
        logging.warning("ELP Erlang analysis unavailable for %s: %s", proj_dir, exc)
        return ErlangAnalysis(functions={}, edges={})
