# [SPEC]
# Unit: src/languages/erlang-py/function_spans.py
#
# function_spans(proj_dir, filepath) -> Optional[List[Tuple[str, int, int]]]
#
# Pre-condition:
#   - proj_dir is a non-empty string path to the project root directory
#   - filepath is a non-empty string path to a source file
#
# Post-condition:
#   - When the Erlang Language Platform (ELP) backend is available and has indexed
#     filepath, returns a list of (func_name, start_line, end_line) tuples for every
#     function definition found in the file
#   - start_line and end_line are 0-based inclusive line numbers within the file
#   - Returns None when the ELP backend is unavailable or filepath has not been
#     indexed, signaling the caller to fall back to a regex-based extractor
#   - The returned list is empty when filepath contains no function definitions and
#     the backend is available
# [SPEC]

# [INFO]
# _analysis_or_empty(proj_dir) -> object
#   Pre-condition: proj_dir is a string path to a project root
#   Post-condition: Returns an object whose .spans attribute is a dict mapping absolute
#     file paths to lists of (func_name, start, end) tuples when the ELP backend is
#     available; returns an object whose .spans attribute is an empty dict when the
#     backend is unavailable
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return ELP function ranges as 0-based inclusive source-line spans."""
    path = os.path.abspath(filepath)
    return _analysis_or_empty(proj_dir).spans.get(path)
