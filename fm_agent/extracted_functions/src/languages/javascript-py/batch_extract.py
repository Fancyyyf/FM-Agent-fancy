# [SPEC]
# Unit: src/languages/javascript-py/batch_extract.py
#
# batch_extract(proj_dir)
#
# Pre-condition:
#   - proj_dir is a string path to a valid project root directory containing JavaScript
#     source files (.js, .jsx).
#
# Post-condition:
#   - If the codegraph backend is available, returns a dictionary mapping each absolute
#     file path (string) to a list of (func_name, func_body) tuples, where func_name is
#     a string and func_body is the source text of the function, for every JavaScript
#     function definition found across all project files.
#   - If the codegraph backend is unavailable, returns an empty dictionary.
#   - Each key in the returned dictionary is an absolute filesystem path; each value is
#     a non-empty list of tuples.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor or None
#   Pre-condition: proj_dir is a valid filesystem path to a project directory.
#   Post-condition: Returns a CodeGraphExtractor instance with a loaded code graph for the
#     project, or None when the backend cannot be initialized for the given directory.
# [SPLIT]
# CodeGraphExtractor.get_functions_by_file(language, proj_dir) -> dict of str to list of (str, str)
#   Pre-condition: language is a valid language key string; proj_dir is a valid project
#     directory path.
#   Post-condition: Returns a dictionary mapping absolute file paths to lists of
#     (func_name, func_body) tuples for all function definitions found in source files
#     of the given language within the project directory.
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all JavaScript files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("javascript", proj_dir) if cg else {}
