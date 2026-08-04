def _normalize_backend(value):
    backend = (value or "").strip().lower()
    if not backend or backend in {"0", "false", "no", "off"}:
        return "opencode"
    if backend == "auto":
        return "auto"
    return _BACKEND_ALIASES.get(backend, backend)
