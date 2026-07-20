# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/erlang-py/_module_from_uri.py
#
# _module_from_uri(uri: str) -> str
#
# Pre-condition:
#   - uri is a non-empty string
#
# Post-condition:
#   - Returns the filename stem (final path component with its last dot-extension removed)
#     of the path portion of uri
#   - Percent-encoded characters in the URI path are decoded before stem extraction
#   - Backslash characters in the decoded path are normalized to forward slash before stem
#     extraction; path components are interpreted using POSIX semantics
#   - Query, fragment, and scheme components of the URI, if present, do not affect the
#     result
#   - The returned string contains no instances of the double-underscore sequence ("__")
#   - The returned string is non-empty
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _module_from_uri(uri: str) -> str:
    path = unquote(urlparse(uri).path)
    return PurePosixPath(path.replace("\\", "/")).stem
