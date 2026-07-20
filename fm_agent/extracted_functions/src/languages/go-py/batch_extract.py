# [SPEC]
# Unit: src/languages/go-py/batch_extract.py
#
# batch_extract(proj_dir) -> Dict[str, List[Tuple[str, str]]]
#
# Pre-condition:
#   - proj_dir is a non-empty string path to a project root containing Go source files
#
# Post-condition:
#   - Returns a dict whose keys are absolute file paths (strings) of Go source files
#     and whose values are lists of (func_name, body) tuples for all function
#     definitions extracted from each file
#   - func_name is a string containing the canonicalized function identifier; body is
#     a string containing the full source text of the function definition
#   - Returns an empty dict {} when no codegraph backend is available for Go
#   - Only .go source files within proj_dir are processed
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> Optional[CodeGraphExtractor]
#   Pre-condition: proj_dir is a valid project root path
#   Post-condition: Returns a CodeGraphExtractor instance configured for the project
#     when a codegraph backend is available; returns None otherwise
# [SPLIT]
# CodeGraphExtractor.get_functions_by_file(lang_key, proj_dir) -> Dict[str, List[Tuple[str, str]]]
#   Pre-condition: lang_key is a language identifier string; proj_dir is the project root
#   Post-condition: Returns a dict mapping absolute file paths to lists of (func_name, body)
#     tuples for all function definitions in files of the given language
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all Go files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("go", proj_dir) if cg else {}
