# [SPEC]
# Unit: src/generate_topdown_layers-py/_file_to_fqn.py
#
# _file_to_fqn(filepath: str, proj_dir: str) -> str
#
# Pre-condition:
#   - filepath is an absolute or relative path to an extracted function file
#     that resides under the directory <proj_dir>/extracted_functions/
#   - proj_dir is the project root directory path
#   - The extracted function file has a filename that includes a file extension
#     (e.g., .py, .cpp, .rs)
#
# Post-condition:
#   - Returns the Fully-Qualified Name (FQN) derived from filepath by:
#     taking the path relative to <proj_dir>/extracted_functions/, stripping
#     the file extension to obtain the stem, and joining all directory
#     components together with the stem using "::" as the separator
#   - The returned FQN consists of one or more "::"-separated segments where
#     the final segment is the filename stem and preceding segments are the
#     directory components below extracted_functions/
#   - Each segment in the returned FQN is a non-empty string containing no
#     "::" substrings
#   - The return value is deterministic for a given (filepath, proj_dir) pair
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _file_to_fqn(filepath, proj_dir):
    """Convert an extracted function file path to its FQN.

    extracted_functions/src/engine/loader-cpp/loadData.cpp -> src::engine::loader-cpp::loadData
    """
    extracted_base = os.path.join(proj_dir, "extracted_functions")
    rel = os.path.relpath(filepath, extracted_base)
    # Strip file extension from the function file itself
    stem, _ = os.path.splitext(rel)
    # Join with :: separator
    parts = Path(stem).parts
    return "::".join(parts)
