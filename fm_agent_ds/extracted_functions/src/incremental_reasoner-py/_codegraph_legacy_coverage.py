def _codegraph_legacy_coverage(proj_dir, codegraph_functions, file_languages):
    """Check that CodeGraph covers every function the legacy extractor sees.

    CodeGraph can legitimately contain *additional* functions, such as an inline
    C++ member that the legacy extractor skips. It is only safe to bypass the
    legacy path when every legacy-visible function has an ordered CodeGraph match
    with the same bare name and source. A missing match means CodeGraph is
    incomplete for this file, so callers must use the legacy fallback instead.
    """
    coverage = {}
    for rel_path, lang_key in file_languages.items():
        rel_key = _normalized_relative_path(proj_dir, rel_path)
        abs_path = os.path.join(proj_dir, rel_path)
        if not os.path.exists(abs_path):
            # Added or removed files only have functions on one side of the
            # comparison; an absent file is therefore an expected empty map.
            coverage[rel_key] = True
            continue
        legacy_functions = extract_functions_from_file(abs_path, lang_key)
        codegraph_items = list(codegraph_functions.get(rel_key, {}).items())
        codegraph_index = 0

        for legacy_name, legacy_source in legacy_functions:
            legacy_body = _normalized_function_source(legacy_source)
            legacy_bare_name = _bare_function_name(legacy_name)
            while codegraph_index < len(codegraph_items):
                identifier, codegraph_source = codegraph_items[codegraph_index]
                codegraph_index += 1
                if (
                    _bare_function_name(identifier) == legacy_bare_name
                    and _normalized_function_source(codegraph_source) == legacy_body
                ):
                    break
            else:
                logging.warning(
                    "CodeGraph does not cover legacy-extracted function %s in %s; "
                    "using legacy comparison for this file.",
                    legacy_name,
                    rel_path,
                )
                coverage[rel_key] = False
                break
        else:
            coverage[rel_key] = True
    return coverage
