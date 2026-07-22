# [SPEC]
# Unit: src/languages/python-py/batch_extract.py
#
# batch_extract(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a string path to a project root directory.
#
# Post-condition:
#   - Returns a dict where each key is an absolute file path (str) and each value is a list of (function_name: str, function_body: str) tuples.
#   - The returned keys correspond to Python source files (.py) discovered under the project directory.
#   - When the CodeGraph backend cannot index the project directory, returns an empty dict (no entries).
#   - Each tuple's function_name identifies a top-level function or method definition in the corresponding source file.
#   - Each tuple's function_body contains the full source text of the function, including its signature and body.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> object | None
#   Pre-condition: proj_dir is a filesystem path to a project root.
#   Post-condition: Returns a CodeGraphExtractor instance configured for the given project, or a falsy value when the backend is unavailable or the project cannot be indexed.
# [SPLIT]
# cg.get_functions_by_file(language: str, proj_dir: str) -> dict
#   Pre-condition: language is a valid language key string (e.g., "python").
#   Post-condition: Returns a dict mapping absolute file paths to lists of (function_name, function_body) tuples for source files of the given language under proj_dir; files that cannot be opened for reading are omitted.
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all Python files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("python", proj_dir) if cg else {}
