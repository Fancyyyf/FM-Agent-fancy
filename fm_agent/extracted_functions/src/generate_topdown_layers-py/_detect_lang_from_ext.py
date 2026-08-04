def _detect_lang_from_ext(filepath):
    """Detect the language key from a file's extension."""
    base = os.path.basename(filepath)
    ext = base.rsplit(".", 1)[-1] if "." in base else ""
    return EXT_TO_LANG.get(ext)
