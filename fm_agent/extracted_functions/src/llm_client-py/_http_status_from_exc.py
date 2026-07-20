# [SPEC]
# Unit: src/llm_client-py/_http_status_from_exc.py
#
# _http_status_from_exc(exc) -> int | None
#
# Pre-condition:
#   - exc is any object
#
# Post-condition:
#   - If exc is an instance of urllib.error.HTTPError, returns the integer HTTP status code stored on exc
#   - If exc is not an instance of urllib.error.HTTPError, returns None
#   - Never raises an exception regardless of input
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _http_status_from_exc(exc):
    """Extract HTTP status from a urllib HTTPError, else None."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code
    return None
