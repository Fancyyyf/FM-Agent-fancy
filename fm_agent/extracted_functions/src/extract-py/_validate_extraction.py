def _validate_extraction(extracted_dir, registry_langs=None):
    """Re-parse every extracted file and verify each contains exactly one function.

    Files for languages that returned data from their REGISTRY backend are skipped:
    those backends write exactly one function body per file by construction, so
    regex re-parsing adds no safety and produces false negatives for forms the
    regex cannot recognise (async def, class methods, arrow functions).

    Returns a list of (file_path, function_count) for files that fail validation.
    """
    failures = []
    for root, _, files in os.walk(extracted_dir):
        for fname in files:
            ext = fname.rsplit('.', 1)[-1] if '.' in fname else ''
            lang_key = EXT_TO_LANG.get(ext)
            if not lang_key:
                continue
            if registry_langs and lang_key in registry_langs:
                continue
            fpath = os.path.join(root, fname)
            funcs = extract_functions_from_file(fpath, lang_key)
            if len(funcs) != 1:
                failures.append((fpath, len(funcs)))
    return failures
