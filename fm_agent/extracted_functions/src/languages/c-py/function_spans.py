# [SPEC]
# Unit: src/languages/c-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - proj_dir is a path to an existing project directory
#   - filepath is a path to a C source file with a ".c" extension
#
# Post-condition:
#   - Returns None when a codegraph instance cannot be initialized from proj_dir
#   - Otherwise returns a list of (function_name, start_idx, end_idx) tuples for every
#     function defined in the C source file at filepath, where start_idx and end_idx
#     are 0-indexed inclusive line numbers
# [SPEC]

# [INFO]
# CodeGraphExtractor.get_function_spans(self, lang_key: str, abs_filepath: str) -> list[tuple[str, int, int]] | None
# Pre-condition: self is a valid CodeGraphExtractor instance; lang_key is a non-empty string;
#   abs_filepath is an absolute filesystem path to a source file residing within the project root.
# Post-condition: Returns None when lang_key is not recognized or the database has no rows for the file
#   (file not indexed, no definitions, or path resolution fails), signalling the caller to fall back to regex extraction.
#   Otherwise returns a list of (name, start_idx, end_idx) for every function/method definition.
#   name is a class-qualified identifier; start_idx and end_idx are 0-indexed inclusive line numbers
#   converted from the backend's 1-indexed representation; list ordered by ascending start_idx.
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one C file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("c", filepath) if cg else None
