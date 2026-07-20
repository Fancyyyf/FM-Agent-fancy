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
# [SPEC]

# [INFO]
# _file_to_fqn(file_path, fm_agent_dir) -> str
#   Pre-condition: file_path is an absolute path to an extracted function file under fm_agent_dir/extracted_functions/; fm_agent_dir is the absolute path to the fm_agent workspace directory
#   Post-condition: Returns the fully-qualified function name derived from file_path by stripping the fm_agent_dir/extracted_functions/ prefix, removing the file extension, and joining remaining path components with "::" separators
# [INFO]

def _modified_function_targets(
    proj_dir, modified_functions, classes=("added", "removed", "modified")
):
    """
    Map the functions recorded in modified_functions to (FQN, extracted-file path).

    modified_functions is the mapping returned by _collect_changed_functions: an
    absolute source-file path -> {"added", "removed", "modified"} lists of function
    names. For each (file, name) pair whose change class is in classes, this computes
    the FQN used by the call graph and the path of the function's file under
    proj_dir/fm_agent/extracted_functions/, both matching that layout (the source
    file's final dot becomes a hyphen and path components are joined with "::"), e.g.
    an "load" function in "<proj_dir>/src/engine/loader.cpp" -> FQN
    "src::engine::loader-cpp::load" at ".../extracted_functions/src/engine/loader-cpp/load.cpp".

    Returns a dict mapping FQN -> absolute extracted-file path.
    """
    extracted_base = os.path.join(proj_dir, "fm_agent", "extracted_functions")
    targets = {}
    for abs_src, changes in modified_functions.items():
        rel = os.path.relpath(abs_src, proj_dir)
        src_dir = os.path.dirname(rel)
        src_base = os.path.basename(rel)
        last_dot = src_base.rfind(".")
        if last_dot > 0:
            dir_name = src_base[:last_dot] + "-" + src_base[last_dot + 1:]
            ext = src_base[last_dot + 1:]
        else:
            dir_name = src_base
            ext = ""
        func_dir = os.path.join(extracted_base, src_dir, dir_name) if src_dir else os.path.join(extracted_base, dir_name)
        names = set()
        for cls in classes:
            names.update(changes.get(cls, []))
        for name in names:
            fname = f"{name}.{ext}" if ext else name
            path = os.path.join(func_dir, fname)
            fqn = _file_to_fqn(path, os.path.join(proj_dir, "fm_agent"))
            targets[fqn] = path
    return targets
