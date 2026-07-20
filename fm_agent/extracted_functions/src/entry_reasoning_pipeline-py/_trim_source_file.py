# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_trim_source_file.py
#
# _trim_source_file(filepath, keep_names, proj_dir=None) -> (kept: int, removed: int)
#
# Pre-condition:
#   - filepath is an absolute path to an existing source file
#   - keep_names is a collection of function name strings to preserve
#   - proj_dir is a project root directory path or None
#
# Post-condition:
#   - When the file extension does not map to a recognized language key in
#     EXT_TO_LANG, the file is left untouched and (0, 0) is returned
#   - When the file has no detected function bodies (spans is empty), the file
#     is left untouched and (0, 0) is returned
#   - When the file has detected function bodies: every function body whose name
#     is a member of keep_names is preserved, every function body whose name is
#     not a member of keep_names is removed, and all source lines that do not
#     belong to any function body are preserved in their original order and form
#   - The source file at filepath is overwritten with the resulting content; the
#     file path does not change
#   - Returns a tuple (kept, removed) where kept is the count of function bodies
#     preserved, removed is the count of function bodies removed, and both are
#     non-negative integers whose sum equals the total number of function bodies
#     detected in the original file
#   - File encoding is preserved (the original raw lines are written back)
# [SPEC]

# [INFO]
# _function_spans(filepath, lang_key, proj_dir) -> (list, list)
#   Pre-condition: filepath is a path to an existing source file; lang_key is
#     a recognized language key for function extraction; proj_dir is a project
#     root directory path or None
#   Post-condition: Returns (spans, raw_lines) where raw_lines is a list of all
#     source lines (str) from the file in original order, and spans is a list of
#     (name, start, end) tuples where name is the function name string, start is
#     the 0-indexed first line of that function body, and end is the 0-indexed
#     last line of that function body (inclusive); the line ranges of distinct
#     spans do not overlap
# [INFO]

def _trim_source_file(filepath, keep_names, proj_dir=None):
    """Delete every function NOT in ``keep_names`` from a source file in place.

    Non-function lines (includes, declarations, globals, etc.) are preserved as
    context; only the line ranges of unselected functions are removed. Returns
    ``(kept, removed)`` counts. Files whose language is unsupported, or that
    contain no detected functions, are left untouched.

    ``proj_dir`` is forwarded to _function_spans so codegraph can locate the
    project's index; when None, function detection falls back to the regex
    extractor.
    """
    ext = os.path.basename(filepath).rsplit(".", 1)[-1] if "." in os.path.basename(filepath) else ""
    lang_key = EXT_TO_LANG.get(ext)
    if not lang_key:
        return 0, 0

    spans, raw_lines = _function_spans(filepath, lang_key, proj_dir)
    if not spans:
        return 0, 0

    drop = set()
    kept = removed = 0
    for name, start, end in spans:
        if name in keep_names:
            kept += 1
        else:
            removed += 1
            drop.update(range(start, end + 1))

    if drop:
        new_lines = [ln for i, ln in enumerate(raw_lines) if i not in drop]
        with open(filepath, "w") as f:
            f.writelines(new_lines)
    return kept, removed
