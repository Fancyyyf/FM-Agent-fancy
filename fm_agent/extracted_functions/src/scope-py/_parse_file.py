def _parse_file(src_path: Path,
                proj_dir: str | None = None) -> tuple[list[dict], list[str], list[dict]] | tuple[None, None, None]:
    """
    Parse a source file into (funcs_info, source_lines, classes).

    Dispatches on the file extension via extract.EXT_TO_LANG: Python files go through the
    ast-based path (with a fall back to the generic extractor if the AST parse fails, e.g.
    on Python 2 syntax), and every other language registered in EXT_TO_LANG goes through
    extract._function_spans (codegraph-backed when proj_dir indexes the file, regex otherwise).
    proj_dir is forwarded so the generic path can use codegraph; Returns (None, None, None)
    for unsupported extensions or unreadable files.
    """
    ext = src_path.suffix.lstrip('.').lower()
    lang_key = EXT_TO_LANG.get(ext)
    if lang_key is None:
        logger.warning("Unsupported extension for %s; cannot scope functions.", src_path)
        return None, None, None

    if lang_key == 'python':
        funcs, source_lines, classes = _parse_python_file(src_path)
        if funcs is not None:
            return funcs, source_lines, classes
        # AST parse failed — fall back to the generic line-based extractor.

    return _parse_generic_file(src_path, lang_key, proj_dir=proj_dir)
