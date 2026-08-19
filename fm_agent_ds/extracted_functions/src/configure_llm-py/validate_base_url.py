def validate_base_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ConfigWizardError(
            f"Base URL must be an absolute http(s) URL, got: {url!r}"
        )
