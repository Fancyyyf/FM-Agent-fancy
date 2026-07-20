# [SPEC]
# Unit: src/generate_topdown_layers-py/_detect_lang_from_ext.py
#
# _detect_lang_from_ext(filepath: str) -> str | None
#
# Pre-condition:
#   - filepath is a non-empty string representing a filesystem path with a
#     file extension (i.e., the final path component contains at least one "."
#     separating a stem from an extension)
#
# Post-condition:
#   - Returns the programming language key string associated with the file's
#     extension in the global language-to-extension mapping; the returned key
#     is one of the language identifiers recognized by the FM-Agent pipeline
#   - Returns None if and only if the file's extension is not present in the
#     language-to-extension mapping
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _detect_lang_from_ext(filepath):
    """Detect the language key from a file's extension."""
    base = os.path.basename(filepath)
    ext = base.rsplit(".", 1)[-1] if "." in base else ""
    return EXT_TO_LANG.get(ext)
