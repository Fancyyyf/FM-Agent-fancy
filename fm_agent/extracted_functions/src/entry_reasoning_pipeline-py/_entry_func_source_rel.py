# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_entry_func_source_rel.py
#
# _entry_func_source_rel(entry_func) -> str
#
# Pre-condition:
#   - entry_func is a non-empty FQN string whose components are delimited by "::"
#   - The last component of entry_func is the function name
#   - The second-to-last component of entry_func is the extraction directory name,
#     which follows the convention of replacing the last "." in the source-filename
#     basename with "-" and appending "-<extension>" (e.g. "loader.cpp" → "loader-cpp")
#
# Post-condition:
#   - Returns a source-file relative path (using "/" separators) derived by
#     reversing the FQN-to-extracted-file-path mapping convention, regardless of
#     the host OS path separator
#   - The returned path identifies the source file that contains the function
#     named by entry_func
# [SPEC]

# [INFO]
# _extracted_file_to_source_rel(extracted_rel) -> str
#   Pre-condition: extracted_rel is a relative path referring to an extracted
#     function file under the extracted_functions/ directory layout
#   Post-condition: Returns the corresponding source-file relative path by
#     reversing the extraction directory naming convention: the extraction
#     directory name <basename>-<ext> is mapped back to <basename>.<ext>, and
#     the function-name file component is removed
#   Post-condition: The returned path uses "/" as the path separator
# [INFO]

def _entry_func_source_rel(entry_func):
    """Map an entry_func FQN back to its source file (project-relative path).

    ``src::engine::loader-cpp::loadData`` -> ``src/engine/loader.cpp``. The FQN's
    last component is the function name and the second-to-last is the extraction
    function directory (``loader-cpp``); reuse the extracted-file inverse mapping
    by treating the ``::``-joined FQN as an extracted-file path.
    """
    extracted_rel = os.path.join(*entry_func.split("::"))
    return _extracted_file_to_source_rel(extracted_rel).replace(os.sep, "/")
