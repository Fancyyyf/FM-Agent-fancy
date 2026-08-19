def _normalized_function_source(source):
    """Normalize line endings before comparing extractor output."""
    return source.replace("\r\n", "\n").replace("\r", "\n")
