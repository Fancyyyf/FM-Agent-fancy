# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_extracted_file_to_source_rel.py
#
# _extracted_file_to_source_rel(extracted_rel) -> str
#
# Pre-condition:
#   - extracted_rel is a relative path whose last path component names a function
#     file and whose parent directory name was derived from a source filename by
#     replacing the last "." with "-"
#
# Post-condition:
#   - Returns the source-file relative path obtained by replacing the last hyphen
#     in the parent directory name with a dot and stripping the function-name file
#     component
#   - When the parent directory name contains no hyphen after its first character,
#     the directory name is returned unchanged and no parent directory prefix is
#     prepended
#   - The returned path uses "/" as the path separator
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _extracted_file_to_source_rel(extracted_rel):
    """Map an extracted-function file path back to its source file (relative).

    Inverse of the extraction layout: ``src/engine/loader-cpp/loadData.cpp``
    (a function file) -> ``src/engine/loader.cpp`` (the source file). Extraction
    builds the function directory by replacing the source filename's last dot
    with a hyphen (``loader.cpp`` -> ``loader-cpp``), so we reverse the last
    hyphen of the directory name.
    """
    func_dir = os.path.dirname(extracted_rel)        # src/engine/loader-cpp
    src_dir = os.path.dirname(func_dir)              # src/engine
    dir_name = os.path.basename(func_dir)            # loader-cpp
    hyphen = dir_name.rfind("-")
    if hyphen > 0:
        source_base = dir_name[:hyphen] + "." + dir_name[hyphen + 1:]
    else:
        source_base = dir_name
    return os.path.join(src_dir, source_base) if src_dir else source_base
