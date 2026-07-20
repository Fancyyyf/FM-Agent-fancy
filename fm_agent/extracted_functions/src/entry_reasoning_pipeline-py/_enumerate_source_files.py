# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_enumerate_source_files.py
#
# _enumerate_source_files(proj_dir) -> list[str]
#
# Pre-condition:
#   - proj_dir is an existing directory path
#
# Post-condition:
#   - Returns a sorted list (ascending lexicographic order) of source-file
#     relative paths (using "/" separators) for every regular file under
#     proj_dir that satisfies ALL of the following:
#     a) Not located within any subdirectory named "fm_agent" or ".git" at any
#        nesting level below proj_dir
#     b) Has a file extension for which EXT_TO_LANG returns a truthy value
#     c) _is_test_file returns False for the relative path
#   - The returned paths are relative to proj_dir
#   - The returned list is in ascending lexicographic order
#   - Files excluded by test-file heuristics are omitted; the test-file
#     exemption for the entry function is a caller-side concern and does not
#     affect this function's output
# [SPEC]

# [INFO]
# _is_test_file(src_rel) -> bool
#   Pre-condition: src_rel is a source-file relative path string using "/"
#     separators
#   Post-condition: Returns True when the file path matches test-file
#     heuristics; returns False otherwise
# [INFO]

def _enumerate_source_files(proj_dir):
    """List every supported, non-test source file under proj_dir (relative paths).

    Skips the fm_agent/ and .git/ directories and applies the same language and
    test-file filters run_extraction uses, so the returned files are exactly the
    ones that will yield extracted functions. The entry_func's source file is
    still included when it looks like a test, because run_entry_pipeline
    registers it as a test-file exemption before selection runs.
    """
    source_files = []
    for root, dirs, files in os.walk(proj_dir):
        dirs[:] = [d for d in dirs if d not in ("fm_agent", ".git")]
        for fname in files:
            src_rel = os.path.relpath(os.path.join(root, fname), proj_dir).replace(os.sep, "/")
            ext = fname.rsplit(".", 1)[-1] if "." in fname else ""
            if EXT_TO_LANG.get(ext) and not _is_test_file(src_rel):
                source_files.append(src_rel)
    return sorted(source_files)
