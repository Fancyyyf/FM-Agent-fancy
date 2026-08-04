def _inject_targets():
    return [s.strip() for s in (settings.inject.hosts or "").split(",") if s.strip()]
