def _matches_inject_target(url, target):
    if target.lower().startswith(("http://", "https://")):
        return url.startswith(target)
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return False
    return host == target or host.endswith("." + target)
