def _parse_generic_file(src_path: Path, lang_key: str,
                        proj_dir: str | None = None) -> tuple[list[dict], list[str], list[dict]] | tuple[None, None, None]:
    """
    Parse a non-Python source into per-function signals, recovering per-function signals
    by regex. Returns no classes (class-scope narrowing is Python-only).

    Function boundaries are located by extract._function_spans, which draws them from
    codegraph when proj_dir indexes the file (the same source of truth run_extraction uses
    to name the extracted-function files) and falls back to extract.py's regex brace/indent
    extractor otherwise. The names it returns are already deduped (foo, foo_1, ...) exactly
    as run_extraction names those files, so a ranked function's 'name' maps straight onto its
    extracted-function file.
    """
    try:
        spans, raw_lines = _function_spans(str(src_path), lang_key, proj_dir=proj_dir)
    except Exception as exc:
        logger.warning("Could not read %s: %s", src_path, exc)
        return None, None, None

    # _function_spans keeps newline characters on raw_lines; strip them the same way
    # extract.py normalizes before extraction so the 0-based span indices line up with
    # source_lines (source_lines[start0] is the signature line).
    source_lines = [l.rstrip('\n').rstrip('\r') for l in raw_lines]
    lang_cfg = LANG_CONFIG[lang_key]

    funcs = [
        _generic_func_info(name, start0, end0, source_lines, lang_cfg)
        for name, start0, end0 in spans
    ]
    return funcs, source_lines, []
