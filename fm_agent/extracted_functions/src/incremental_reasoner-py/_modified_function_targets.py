# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_modified_function_targets.py
#
# _modified_function_targets(proj_dir, modified_functions, classes=("added", "removed", "modified")) -> dict[str, str]
#
# Pre-condition:
#   - proj_dir is an absolute path to a project root directory whose
#     fm_agent/extracted_functions/ subdirectory exists
#   - modified_functions is a dict mapping absolute source-file paths to dicts, where
#     each inner dict has string-valued keys drawn from {"added", "removed", "modified"}
#     with list-of-string values (function names declared in that source file)
#   - classes is a non-empty tuple of string-valued change-category labels drawn from
#     {"added", "removed", "modified"}
#
# Post-condition:
#   - Returns a dict mapping each fully-qualified function name (FQN) to the absolute
#     filesystem path of the corresponding extracted-function file under
#     proj_dir/fm_agent/extracted_functions/
#   - A (source-file, function-name) pair is included when the function name appears in
#     at least one of the change-category lists specified by classes within
#     modified_functions
#   - Function names whose change categories all fall outside classes are excluded from
#     the result
#   - The FQN key is derived from the extracted-function file path via the project's FQN
#     convention: the fm_agent/extracted_functions/ prefix is stripped, the file
#     extension is removed, and remaining path components are joined with "::"
#     separators, where the source file's final dot was already replaced by a hyphen
#     in the extracted-function directory name
#   - The extracted-function file path follows the extracted_functions/ layout
#     convention: the source file's relative path from proj_dir has its final dot
#     replaced by a hyphen to form the directory name, and each function name with the
#     source file's original extension forms the leaf filename
#   - When a source file's basename contains no dot, the directory name is the basename
#     unchanged and the leaf filename has no extension
#   - When the same function name appears in multiple change-category lists for the
#     same source file, it is included exactly once
#   - For each source file, the function directory is resolved via _src_rel_to_func_dir,
#     and the available extracted-function files are indexed by bare method name via
#     _extracted_files_by_method
#   - For each changed function name, the function first looks for an exact match in the
#     method-name index; if no match is found, it strips a trailing “_\d+” suffix (a
#     regex deduplication disambiguator) from the name and retries with the resulting
#     stem
#   - When a bare name or its stem matches multiple extracted-function files (e.g.,
#     because two classes in the source file define a method with the same name), every
#     matching file is included in the result
# [SPEC]

# [INFO]
# _file_to_fqn(file_path, fm_agent_dir) -> str
#   Pre-condition: file_path is an absolute path to an extracted function file under fm_agent_dir/extracted_functions/; fm_agent_dir is the absolute path to the fm_agent workspace directory
#   Post-condition: Returns the fully-qualified function name derived from file_path by stripping the fm_agent_dir/extracted_functions/ prefix, removing the file extension, and joining remaining path components with "::" separators
#
# _src_rel_to_func_dir(proj_dir, abs_src) -> tuple[str, str]
#   Pre-condition: proj_dir is an absolute directory path; abs_src is an absolute file path within proj_dir
#   Post-condition: Returns a tuple (func_dir, ext). func_dir is an absolute directory path formed by taking the relative path of abs_src with respect to proj_dir, splitting into directory parts and a basename, replacing the last dot in the basename with a hyphen (if the dot is not the first character; otherwise the basename is unchanged), and concatenating proj_dir/fm_agent/extracted_functions, the directory parts, and the modified basename. ext is the substring of the basename after the last dot when that dot appears after the first character, otherwise ext is the empty string. The result depends only on the string content of the arguments.
#
# _extracted_files_by_method(func_dir) -> dict[str, list[str]]
#   Pre-condition: func_dir is a filesystem path (which may or may not be an existing directory)
#   Post-condition: Returns a mutable dict-like mapping from string keys to lists of absolute paths. If func_dir is not an existing directory, the mapping is empty. Otherwise, every regular file reachable by recursive descent is indexed: its stem (base name without the final dot-separated extension) always becomes a key, and if the stem contains "::", the substring after the last "::" (the bare method name) becomes an additional key for that file. The list for each key contains the absolute paths in traversal order, with at least one entry per key. Accessing a missing key returns an empty list without raising an error; mutating a returned list does not affect the mapping.
# [INFO]

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
