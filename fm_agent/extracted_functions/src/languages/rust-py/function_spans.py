# [SPEC]
# Unit: src/languages/rust.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - proj_dir is a filesystem path to a project directory
#   - filepath is a path to a single Rust source file within the project
#
# Post-condition:
#   - If codegraph is available and indexes filepath: returns a list of
#     (function_name, start_line, end_line) tuples, one per top-level function
#     declared in the file. Each start_line and end_line is a 0-indexed
#     inclusive line number bounding the function's source span.
#   - If filepath contains no top-level function declarations: returns an
#     empty list.
#   - If codegraph is unavailable or does not index filepath: returns None.
#     A None return signals the caller to fall back to regex-based extraction.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a filesystem path to a project directory
#   Post-condition: Returns an initialized CodeGraphExtractor instance for the
#     project at proj_dir, or None when the codegraph backend cannot be initialized
# [SPLIT]
# CodeGraphExtractor.get_function_spans(lang_key: str, abs_filepath: str) -> list[tuple[str, int, int]] | None
#   Pre-condition: lang_key is a non-empty string identifying a programming language;
#     abs_filepath is an absolute filesystem path to a source file residing within the
#     project root
#   Post-condition: Returns None when lang_key is not recognized by the codegraph backend
#     or when the database contains no rows for the given file; otherwise returns a list
#     of (name, start_idx, end_idx) tuples for every function and method definition
#     detected, with 0-indexed inclusive line indices, ordered by ascending start_idx
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one Rust file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("rust", filepath) if cg else None
