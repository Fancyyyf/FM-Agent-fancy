# [SPEC]
# Unit: src/llm_client-py/_read_error_body.py
#
# _read_error_body(exc, limit=800) -> str
#
# Pre-condition:
#   - exc is an object whose read() method, called with no arguments, returns the raw response body as bytes, or raises any exception
#   - limit is a positive integer (default 800) specifying the maximum character count of the returned string
#
# Post-condition:
#   - Returns the raw HTTP response body decoded as UTF-8 text, with undecodable bytes replaced by the Unicode replacement character (U+FFFD), and leading/trailing whitespace stripped
#   - When the decoded, stripped text exceeds limit characters, the returned string is truncated to the first limit characters and suffixed with a single "…" (ellipsis) character
#   - Returns an empty string when: read() raises any exception, read() returns a falsy value, or the decoded text after stripping is empty
#   - The function tolerates any exception type from read() — callers can invoke it on any exception object without risk of secondary failures
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _read_error_body(exc, limit=800):
    """The raw response body of an HTTPError (the relay's actual error page),
    which str(exc) drops — only `HTTP Error 504: Gateway Time-out` survives
    otherwise. Read-once and tolerant; returns '' if unavailable."""
    try:
        raw = exc.read()
    except Exception:
        return ""
    if not raw:
        return ""
    text = raw.decode("utf-8", "replace").strip()
    return text[:limit] + ("…" if len(text) > limit else "")
