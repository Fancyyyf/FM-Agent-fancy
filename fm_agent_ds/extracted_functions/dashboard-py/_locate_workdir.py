def _locate_workdir(proj_dir):
    """Resolve which fm_agent workdir to monitor.

    Accepts either:
      - A project root: dashboard looks for <root>/fm_agent/ (the live workspace).
      - A workspace directly (any name like fm_agent.opus_partial_*): detected
        by the presence of a `trace/` subdir, used as-is.
    """
    p = Path(proj_dir).resolve()
    if (p / "trace").is_dir():
        return p
    return p / "fm_agent"
