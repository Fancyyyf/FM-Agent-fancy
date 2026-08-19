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
            function_path = os.path.abspath(path)
            valid.add(function_path)
            valid.add(f"{function_path}.spec.json")
            valid.add(f"{function_path}.info.json")

    for root, _dirs, fnames in os.walk(func_dir):
        for fn in fnames:
            abs_path = os.path.abspath(os.path.join(root, fn))
            if abs_path not in valid:
                os.remove(abs_path)

    # Prune empty directories left behind (deepest first).
    for root, _dirs, _files in os.walk(func_dir, topdown=False):
        if root != func_dir and os.path.isdir(root) and not os.listdir(root):
            os.rmdir(root)
