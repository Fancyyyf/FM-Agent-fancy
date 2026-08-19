def _module_from_uri(uri: str) -> str:
    path = unquote(urlparse(uri).path)
    return PurePosixPath(path.replace("\\", "/")).stem
