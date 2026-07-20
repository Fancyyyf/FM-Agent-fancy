# [SPEC]
# Unit: fm_agent/extracted_functions/src/scope-py/_parse_file.py
#
# _parse_file(src_path: Path, proj_dir: str | None = None)
#     -> tuple[list[dict], list[str], list[dict]] | tuple[None, None, None]
#
# Pre-condition:
#   - src_path is a Path to a source file that exists on disk.
#   - proj_dir, if provided, is a string path to a project root directory;
#     it is used when the parser requires project‑level indexing.
#
# Post-condition:
#   - If the file extension is registered as a supported language, returns a
#     tuple (funcs_info, source_lines, classes) where:
#       * funcs_info is a list of dicts, each describing a top‑level function
#         defined in the file, with at minimum 'name' (str), 'start' (int,
#         1‑based start line), and 'end' (int, 1‑based end line) keys.
#       * source_lines is a list[str] containing the source text of the file,
#         one element per line, preserving the original line order.
#       * classes is a list of dicts, each describing a class defined in the
#         file.
#   - If the file extension is not registered as a supported language, or if
#     language‑specific parsing fails for every available parser for that
#     language, returns (None, None, None).
#   - For Python files, parsing is attempted via AST first; if the AST parse
#     fails, a line‑based fallback parser is used.
#   - For non‑Python registered languages, a line‑based parser is used.
#   - The function does not modify the source file.
# [SPEC]

# [INFO]
# _parse_python_file(src_path: Path) -> tuple[list[dict], list[str], list[dict]] | None
#   Pre-condition: src_path is a Path to an existing Python source file.
#   Post-condition: If the file can be parsed as valid Python, returns (funcs_info, source_lines, classes) where funcs_info describes each top‑level function with at minimum 'name', 'start', and 'end' keys, source_lines is the source text as a list of lines, and classes describes each class in the file. If the AST parse fails, returns None.
# [SPLIT]
# _parse_generic_file(src_path: Path, lang_key: str, proj_dir: str | None) -> tuple[list[dict], list[str], list[dict]] | tuple[None, None, None]
#   Pre-condition: src_path is a Path to an existing source file; lang_key is a non‑empty string identifying the language.
#   Post-condition: If the file can be parsed, returns (funcs_info, source_lines, classes) with the same structure as _parse_python_file. If the file cannot be parsed, returns (None, None, None).
# [INFO]

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
