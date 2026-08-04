def _http_status_from_exc(exc):
    """Extract HTTP status from a urllib HTTPError, else None."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code
    return None
