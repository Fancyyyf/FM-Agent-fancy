def _read_error_body(exc, limit=800):
    """The raw response body of an HTTPError (the relay's actual error page),
    which str(exc) drops — only `HTTP Error 504: Gateway Time-out` survives
    otherwise. Read-once and tolerant; returns '' if unavailable."""
    try:
        raw = exc.read()
    except Exception:
        return ""
    if not raw:
        return ""
    text = raw.decode("utf-8", "replace").strip()
    return text[:limit] + ("…" if len(text) > limit else "")
