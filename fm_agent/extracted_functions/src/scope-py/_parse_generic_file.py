# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_parse_generic_file.py
#
# _parse_generic_file(src_path: Path, lang_key: str,
#                     proj_dir: str | None = None) -> tuple[list[dict], list[str], list[dict]] | tuple[None, None, None]
#
# Pre-condition:
#   - src_path is a Path identifying an existing source file on disk.
#   - lang_key is a non‑empty string identifying a language registered in the
#     parser configuration.
#   - proj_dir, if provided, is a string path to a project root directory used
#     for codegraph‑backed function boundary detection.
#
# Post-condition:
#   - If the file can be read and function boundaries can be determined, returns
#     (funcs_info, source_lines, []) where:
#     * funcs_info is a list of dicts, each representing one top‑level function
#       defined in the file, with at minimum 'name' (str), 'start' (int, 1‑based
#       start line), and 'end' (int, 1‑based end line) keys.
#     * source_lines is a list[str] containing one element per line of the file,
#       in order, with trailing '\n' and '\r' removed from each element.
#     * The third element is always an empty list (class‑scope narrowing is
#       Python‑only).
#   - If the file cannot be read or function boundaries cannot be determined,
#     returns (None, None, None).
#   - The function does not modify the source file.
# [SPEC]

# [INFO]
# _function_spans(filepath: str, lang_key: str, proj_dir: str | None) -> tuple[list[tuple[str, int, int]], list[str]]
#   Pre-condition: filepath is a string identifying an existing source file; lang_key is a non‑empty language key.
#   Post-condition: Returns (spans, raw_lines) where spans is a list of (name, start0, end0) tuples with 0‑based line indices identifying function boundaries, and raw_lines is a list of strings containing the file's lines. Raises an exception if the file cannot be read or function boundaries cannot be determined.
# [SPLIT]
# _generic_func_info(name: str, start0: int, end0: int, source_lines: list[str], lang_cfg: dict) -> dict
#   Pre-condition: name is a non‑empty function name; start0 and end0 are 0‑based line indices (start0 ≤ end0); source_lines is a list[str] with at least end0 + 1 elements; lang_cfg is a dict with the parsed‑language configuration.
#   Post-condition: Returns a dict with at minimum 'name' (str, the given name), 'start' (int, 1‑based start line), and 'end' (int, 1‑based end line) keys, plus any language‑specific signal fields extracted from the function body.
# [INFO]

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
