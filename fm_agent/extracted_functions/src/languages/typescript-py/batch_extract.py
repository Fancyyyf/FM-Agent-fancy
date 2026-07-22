# [SPEC]
# Unit: src/languages/typescript.py
#
# batch_extract(proj_dir: str) -> dict[str, list[tuple[str, str]]]
#
# Pre-condition:
#   - proj_dir is a filesystem path to a project directory
#
# Post-condition:
#   - If codegraph is available: returns a dict whose keys are absolute file
#     paths to TypeScript source files within proj_dir, and whose values are
#     lists of (function_name, function_body) tuples for every top-level
#     function declared in the corresponding file.
#   - Each function_name is the identifier of the function declaration.
#   - Each function_body is the full source text of the function definition.
#   - If proj_dir contains no TypeScript files with top-level functions:
#     returns an empty dict.
#   - If codegraph is unavailable: returns an empty dict {}.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a filesystem path to a project directory
#   Post-condition: Returns an initialized CodeGraphExtractor instance for the
#     project at proj_dir, or None when the codegraph backend cannot be initialized
# [SPLIT]
# CodeGraphExtractor.get_functions_by_file(language: str, proj_dir: str) -> dict[str, list[tuple[str, str]]]
#   Pre-condition: language is a string; proj_dir is a string path to a directory
#   Post-condition: Returns a dict mapping absolute file paths to lists of
#     (function_name, function_body) tuples for source files of the given
#     language found under proj_dir. Source files that cannot be opened are
#     omitted without error. When language is not recognized, returns an empty
#     dict.
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all TypeScript files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("typescript", proj_dir) if cg else {}
