# [SPEC]
# Unit: src/incremental_reasoner-py/_reconcile_extracted_dir.py
#
# _reconcile_extracted_dir(proj_dir, abs_src) -> None
#
# Pre-condition:
#   - proj_dir is an absolute path to the project root directory
#   - abs_src is an absolute path to a source file within proj_dir
#
# Post-condition:
#   - Let (func_dir, ext) be the pair that maps abs_src to the extracted-functions
#     directory and source extension via the same naming convention used by
#     run_extraction. If func_dir is not an existing directory on disk, no
#     filesystem changes occur and the function returns.
#   - Otherwise, the set of expected extracted-function files for abs_src is
#     determined:
#     * When abs_src exists on disk and its file extension maps to a language
#       recognized by the project's language registry, the expected files are
#       derived from the current function spans of abs_src. Each span's
#       deduplicated identifier forms an expected filename: the identifier
#       suffixed with ".<ext>" when ext is non-empty, or the bare identifier
#       when ext is empty. The span boundaries are computed with the same
#       backend (codegraph when it indexes the file, otherwise regex) that
#       run_extraction uses.
#     * When abs_src does not exist on disk, or when its extension is not
#       recognized, the set of expected files is empty.
#   - Every file reachable by recursively walking func_dir whose absolute path
#     does not match an expected file path is deleted. Expected files are
#     preserved with their contents unchanged.
#   - After file deletion, every subdirectory of func_dir — excluding func_dir
#     itself — that contains neither files nor subdirectories is removed.
# [SPEC]

# [INFO]
# _function_spans(filepath, lang_key, proj_dir=None) -> ([(str, int, int)], [str])
#   Pre-condition: filepath is a readable source file path, lang_key is a valid language key
#   Post-condition: Returns (spans, raw_lines) where spans is a list of
#     (name, start_idx, end_idx) tuples with 0-based line indices for each
#     top-level function in the file, ordered by first appearance. name is
#     the canonicalized, deduplicated identifier matching the filename that
#     run_extraction writes — the first occurrence of a canonicalized name
#     is used verbatim, and each subsequent occurrence is suffixed with _N
#     where N starts at 1. When proj_dir is provided and codegraph indexes
#     the file, function boundaries are determined by codegraph; otherwise
#     by language-specific regex extraction.
# [SPLIT]
# _src_rel_to_func_dir(proj_dir, abs_src) -> (str, str)
#   Pre-condition: proj_dir is an absolute directory path, abs_src is an
#     absolute file path within proj_dir
#   Post-condition: Returns (func_dir, ext) where func_dir is the absolute
#     directory path under proj_dir/fm_agent/extracted_functions/ that
#     run_extraction would use for abs_src, formed by stripping proj_dir
#     from abs_src to get a relative path, partitioning it into directory
#     components and a basename, and replacing the last dot in the basename
#     with a hyphen to produce the terminal directory name — unless the
#     basename contains no dot after its first character, in which case the
#     terminal directory name is the basename unchanged. ext is the portion
#     of the basename after the last dot when that dot occurs after the
#     first character, or an empty string otherwise. The return values
#     depend only on the string content of the arguments.
# [INFO]

def _reconcile_extracted_dir(proj_dir, abs_src):
    """Delete extracted-function files under abs_src's function directory that
    codegraph no longer produces for it, then prune emptied directories.

    ``valid`` is computed with the same backend (codegraph when it indexes the
    file, else regex) that run_extraction used to write the files, so their
    identifiers — and therefore the on-disk layout — agree; only genuinely orphaned
    files are removed. A source file that no longer exists yields an empty ``valid``
    set, so all of its extracted files are removed.
    """
    func_dir, ext = _src_rel_to_func_dir(proj_dir, abs_src)
    if not os.path.isdir(func_dir):
        return

    valid = set()
    lang_key = EXT_TO_LANG.get(ext)
    if lang_key and os.path.isfile(abs_src):
        spans, _raw = _function_spans(abs_src, lang_key, proj_dir)
        for ident, _s, _e in spans:
            # ident is the class-qualified, deduped identifier written by
            # run_extraction as a flat file that keeps the "::" in its name.
            path = os.path.join(func_dir, ident) + (f".{ext}" if ext else "")
            valid.add(os.path.abspath(path))

    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.abspath(os.path.join(root, fn))
            if abs_path not in valid:
                os.remove(abs_path)

    # Prune empty directories left behind (deepest first).
    for root, _dirs, _files in os.walk(func_dir, topdown=False):
        if root != func_dir and os.path.isdir(root) and not os.listdir(root):
            os.rmdir(root)
