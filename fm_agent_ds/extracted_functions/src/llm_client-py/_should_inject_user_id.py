def _should_inject_user_id(base_url):
    url = (base_url or "").rstrip("/")
    return any(_matches_inject_target(url, target) for target in _inject_targets())
