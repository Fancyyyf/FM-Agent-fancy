# [SPEC]
# Unit: src/languages/cpp-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list | None
#
# Pre-condition:
#   - proj_dir is a valid path to a project directory on the filesystem
#   - filepath is a string identifying a C++ source file within the project
#
# Post-condition:
#   - Returns None when a codegraph backend is unavailable or does not index the file, signaling the caller to fall back to regex-based extraction
#   - Otherwise returns a list of (name, start_idx, end_idx) tuples, each identifying one function in the file by its name and the range of source lines it occupies
#   - In every returned tuple, start_idx and end_idx are 0-indexed inclusive line indices
#   - The returned list covers every function that the codegraph backend detects in the file
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str)
#   Pre-condition: proj_dir is a valid path to a project directory on the filesystem
#   Post-condition: Returns a CodeGraphExtractor instance for the project if the codegraph backend is available, or a falsy value otherwise
# [SPLIT]
# cg.get_function_spans(lang_key: str, filepath: str) where lang_key="cpp"
#   Pre-condition: cg is a valid CodeGraphExtractor instance bound to the project
#   Post-condition: Returns a list of (name, start, end) tuples for functions found in the given file, or None if the file is not indexed
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one C++ file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("cpp", filepath) if cg else None
