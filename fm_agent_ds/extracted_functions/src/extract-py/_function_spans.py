def _function_spans(filepath, lang_key, proj_dir=None):
    """Return ``(spans, raw_lines)`` for a source file.

    ``spans`` is a list of ``(deduped_name, start_idx, end_idx)`` line ranges,
    one per function, named exactly as run_extraction names the extracted files
    (duplicate names get ``_1``, ``_2``, ... suffixes). ``raw_lines`` are the
    file's original lines (newline characters preserved) so callers can rewrite
    the file by line index.

    Function boundaries come from codegraph via the language registry when
    ``proj_dir`` is given and codegraph indexes the file; otherwise they fall
    back to the regex extractor (_extract_functions_brace / _indent). Both
    backends yield the same (name, start_idx, end_idx) shape, so the dedup
    naming below is identical regardless of which one is used.
    """
    lang_cfg = LANG_CONFIG[lang_key]
    with open(filepath, "r", errors="replace") as f:
        raw_lines = f.readlines()
    # Extraction operates on newline-stripped lines; indices line up 1:1 with
    # raw_lines (readlines yields one entry per line).
    norm_lines = [l.rstrip("\n").rstrip("\r") for l in raw_lines]

    raw_funcs = None
    if proj_dir is not None:
        raw_funcs = function_spans_for_file(proj_dir, filepath, lang_key)
    if raw_funcs is None:
        if lang_cfg["body"] == "brace":
            raw_funcs = _extract_functions_brace(norm_lines, lang_key, lang_cfg)
        else:
            raw_funcs = _extract_functions_indent(norm_lines, lang_cfg)

    name_counts = {}
    spans = []
    for name, start, end in raw_funcs:
        cname = canonicalize(name)
        count = name_counts.get(cname, 0)
        name_counts[cname] = count + 1
        deduped = cname if count == 0 else f"{cname}_{count}"
        spans.append((deduped, start, end))
    return spans, raw_lines
