def _modified_function_targets(
    proj_dir, modified_functions, classes=("added", "removed", "modified")
):
    """
    Map the functions recorded in modified_functions to (FQN, extracted-file path).

    modified_functions is the mapping returned by _collect_changed_functions: an
    absolute source-file path -> {"added", "removed", "modified"} lists of function
    names, which the regex change detector reports without a class (``Flush``,
    ``Flush_1``). The extracted files, however, keep codegraph's class qualifier in
    the filename (``.../storage-cpp/LocalStorage::Flush.cpp``), so we do not
    reconstruct a path from the bare name — we walk the function directory and match
    each changed name against the actual files by their bare method tail (tolerating
    the regex dedup suffix). When two classes in one file share a
    method name, a changed bare name maps to both members; that is a safe
    over-approximation for the callers (spec/verify seeds).

    Returns a dict mapping FQN -> absolute extracted-file path.
    """
    work_dir = os.path.join(proj_dir, "fm_agent")
    targets = {}
    for abs_src, changes in modified_functions.items():
        func_dir, _ext = _src_rel_to_func_dir(proj_dir, abs_src)
        by_method = _extracted_files_by_method(func_dir)
        names = set()
        for cls in classes:
            names.update(changes.get(cls, []))
        for name in names:
            paths = list(by_method.get(name, ()))
            if not paths:
                # The regex extractor disambiguates same-name funcs as foo/foo_1;
                # codegraph uses the class qualifier instead, so fall back to the
                # stem.
                stem = re.sub(r"_\d+$", "", name)
                paths = by_method.get(stem, ())
            for path in paths:
                targets[_file_to_fqn(path, work_dir)] = path
    return targets
