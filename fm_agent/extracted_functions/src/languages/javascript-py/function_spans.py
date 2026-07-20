# [SPEC]
# Unit: src/languages/javascript-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple] | None
#
# Pre-condition:
#   - proj_dir is a path to an existing project directory.
#   - filepath is a path to a JavaScript source file within the project.
#
# Post-condition:
#   - Returns None when the codegraph backend is unavailable for the project, or when the
#     backend exists but does not index the given file.
#   - Otherwise returns a list of (name, start_idx, end_idx) tuples, one per function
#     defined in the file.
#   - start_idx and end_idx are 0-indexed inclusive line numbers.
#   - The list is ordered by appearance (ascending start_idx).
#   - The list is empty when no functions are defined in the file.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid path to the project root.
#   Post-condition: Returns a configured codegraph extractor instance, or None if the
#     codegraph backend is not available or cannot index the project.
# [SPLIT]
# cg.get_function_spans(language_key: str, filepath: str) -> list[tuple] | None
#   Pre-condition: cg is a successfully constructed CodeGraphExtractor; language_key is a
#     recognized language identifier; filepath is a source file path within the project.
#   Post-condition: Returns a list of (name, start_line, end_line) tuples for each function
#     in the file with 0-indexed inclusive line numbers, or None when the file is not
#     indexed by the backend.
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one JavaScript file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("javascript", filepath) if cg else None
