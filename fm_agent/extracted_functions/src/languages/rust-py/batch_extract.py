# [SPEC]
# Unit: src/languages/rust-py/batch_extract.py
#
# batch_extract(proj_dir) -> dict
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path to a project directory
#
# Post-condition:
#   - Returns a dictionary where each key is an absolute filesystem path (str) to a Rust source
#     file located within or under the project directory
#   - Each value is a non-empty list of (str, str) tuples: the first element is a function name
#     declared in that file, and the second element is the complete source text of the function body
#   - A source file containing N detected functions produces N entries in its value list
#   - Returns an empty dictionary when no Rust codegraph backend is available for the given project
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a string representing a valid project directory path
#   Post-condition: Returns a configured CodeGraphExtractor instance for the project when the
#     backend initializes successfully; returns None when the backend cannot be initialized
# [SPLIT]
# CodeGraphExtractor.get_functions_by_file(lang, proj_dir) -> dict
#   Pre-condition: lang is a recognized language key string and proj_dir is the project root path
#   Post-condition: Returns a dictionary mapping each absolute source-file path (str) to a list of
#     (function_name, function_body) tuples for all source files of the given language
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all Rust files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("rust", proj_dir) if cg else {}
