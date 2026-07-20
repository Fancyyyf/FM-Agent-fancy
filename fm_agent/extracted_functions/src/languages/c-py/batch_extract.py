# [SPEC]
# Unit: src/languages/c-py/batch_extract.py
#
# batch_extract(proj_dir) -> dict
#
# Pre-condition:
#   - proj_dir is a path to an existing directory containing C source files
#
# Post-condition:
#   - Returns a dictionary mapping absolute file paths to lists of
#     (function_name, function_body) tuples for every C function extracted
#     from the project using codegraph analysis
#   - Returns an empty dictionary {} when codegraph initialization fails
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is an existing directory
#   Post-condition: Returns an initialized CodeGraphExtractor for the project
#     whose build artifacts and source tree are indexed; returns None when
#     initialization cannot complete
# [SPLIT]
# CodeGraphExtractor.get_functions_by_file(language_key, proj_dir) -> dict
#   Pre-condition: language_key is a valid language identifier; proj_dir is the
#     project root directory
#   Post-condition: Returns a dict mapping absolute file paths to lists of
#     (func_name, func_body) tuples for all functions in files of the given
#     language within the project
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all C files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("c", proj_dir) if cg else {}
