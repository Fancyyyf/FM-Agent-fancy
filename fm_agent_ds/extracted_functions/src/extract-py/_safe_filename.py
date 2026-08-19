def _safe_filename(name: str, ext: str) -> str:
    """Return a safe filename from a function name and extension.

    Replaces "/" (directory separator) with "_" and falls back to
    "_function" for empty names.  Does *not* strip leading or trailing
    underscores so that names like __init__ and _private stay consistent
    with codegraph call-edge keys and FQN resolution.
    """
    safe = name.replace('/', '_')
    if not safe:
        safe = "_function"
    return f"{safe}.{ext}"
