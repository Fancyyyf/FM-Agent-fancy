def batch_extract_all(proj_dir: str) -> tuple:
    """Call batch_extract for every registered language and merge results.

    Returns (funcs, langs) where funcs is {abs_filepath: [(func_name, body)]}
    and langs is the set of language keys that returned data.
    """
    funcs = {}
    langs = set()
    for lang, handler in REGISTRY.items():
        result = handler.batch_extract(proj_dir)
        if result:
            funcs.update(result)
            langs.add(lang)
    return funcs, langs
