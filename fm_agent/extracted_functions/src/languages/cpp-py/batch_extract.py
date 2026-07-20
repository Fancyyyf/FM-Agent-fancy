# [SPEC]
# Unit: src/languages/cpp-py/batch_extract.py
#
# batch_extract(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a non-empty string representing a directory path that
#     contains C++ source files (.cpp, .cc, .cxx) and may have a codegraph
#     index (.codegraph/codegraph.db).
#
# Post-condition:
#   - Returns a dictionary where each key is an absolute file path (str) and
#     each value is a list of (function_name: str, body: str) tuples.
#   - Every key corresponds to a C++ source file under proj_dir for which
#     codegraph extracted at least one top-level function.
#   - Each function_name is the canonical name of a function defined in the
#     corresponding source file.
#   - Each body is the full source text of that function as returned by
#     codegraph.
#   - If codegraph is not available for proj_dir (CodeGraphExtractor.from_proj_dir
#     returns a falsy value), the returned dictionary is empty.
#   - The returned dictionary does not include entries for non-C++ files or for
#     files from which codegraph extracted zero functions.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid directory path.
#   Post-condition: Returns a CodeGraphExtractor instance bound to proj_dir if
#     codegraph is available and its index is built for the project; returns a
#     falsy value (None or equivalent) if codegraph is unavailable or
#     initialization fails.
# [SPLIT]
# CodeGraphExtractor.get_functions_by_file(lang_key: str, proj_dir: str) -> dict[str, list[tuple[str, str]]]
#   Pre-condition: lang_key is a language identifier string recognized by the
#     extractor (e.g., "cpp"); proj_dir is the project root used during
#     initialization.
#   Post-condition: Returns a dictionary mapping absolute file paths (str) to
#     lists of (function_name: str, body: str) tuples, covering all top-level
#     functions in files matching lang_key under proj_dir. Returns an empty
#     dictionary if no matching functions are found.
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return {abs_filepath: [(func_name, body)]} for all C++ files."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_functions_by_file("cpp", proj_dir) if cg else {}
