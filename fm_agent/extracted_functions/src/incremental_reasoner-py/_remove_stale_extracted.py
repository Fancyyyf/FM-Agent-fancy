# [SPEC]
# Unit: src/incremental_reasoner-py/_remove_stale_extracted.py
#
# _remove_stale_extracted(proj_dir, modified_functions) -> None
#
# Pre-condition:
#   - proj_dir is an absolute path to the project root directory, under which a child path fm_agent/extracted_functions/ exists
#   - modified_functions is a dict mapping absolute source-file paths to dicts, each having at minimum a "removed" key whose value is a list of function names declared in that source file
#
# Post-condition:
#   - For every function name appearing in any "removed" list within modified_functions, the corresponding extracted-function file under fm_agent/extracted_functions/ no longer exists on the filesystem
#   - For every function directory under fm_agent/extracted_functions/ that contained only files deleted by this operation, the directory itself no longer exists
#   - Every file and directory under fm_agent/extracted_functions/ whose function does not appear in any "removed" list is unchanged
# [SPEC]

# [INFO]
# _modified_function_targets(proj_dir, modified_functions, classes=("removed",)) -> dict[str, str]
#   Pre-condition: proj_dir is a valid project root path; modified_functions is a dict mapping source file paths to change-info dicts with at least the key "removed"; classes is a tuple of change-category strings to select
#   Post-condition: Returns a dict mapping each source-file path to the absolute filesystem path of the extracted-function file for the first function whose change category is in classes; functions whose categories do not intersect classes are excluded
# [INFO]

def _remove_stale_extracted(proj_dir, modified_functions):
    """
    Delete extracted-function files for functions reported as removed (including every
    function of a deleted source file), and prune any function directory left empty as
    a result. Re-extraction never rewrites these files, so without this they linger as
    stale specs under fm_agent/extracted_functions/.
    """
    removed = _modified_function_targets(
        proj_dir, modified_functions, classes=("removed",)
    )
    for path in removed.values():
        if os.path.isfile(path):
            os.remove(path)
    for path in removed.values():
        func_dir = os.path.dirname(path)
        if os.path.isdir(func_dir) and not os.listdir(func_dir):
            os.rmdir(func_dir)
