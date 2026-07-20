# [SPEC]
# Unit: src/extract-py/_safe_filename.py
#
# _safe_filename(name, ext) -> str
#
# Pre-condition:
#   - name is a string (may be empty)
#   - ext is a string representing a file extension
#
# Post-condition:
#   - Returns a string in the form "<safe_name>.<ext>", where safe_name is derived from
#     name and ext is used verbatim
#   - When name is non-empty after the replacement described below, safe_name is name
#     with every occurrence of the "/" character replaced by "_"
#   - When name is empty or consists solely of "/" characters (becoming an empty string
#     after replacement), safe_name is the literal string "_function"
#   - Leading and trailing underscore characters in name are preserved unchanged in
#     safe_name
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _safe_filename(name: str, ext: str) -> str:
    """Return a safe filename from a function name and extension.

    Replaces "/" (directory separator) with "_" and falls back to
    "_function" for empty names.  Does *not* strip leading or trailing
    underscores so that names like __init__ and _private stay consistent
    with codegraph call-edge keys and FQN resolution.
    """
    safe = name.replace('/', '_')
    if not safe:
        safe = "_function"
    return f"{safe}.{ext}"
