# [SPEC]
# Unit: src/languages/go-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list | None
#
# Pre-condition:
#   - proj_dir is a non-empty string referencing a project directory.
#   - filepath is a string identifying a Go source file within that project.
#
# Post-condition:
#   - Returns a list of (function_name, start_line, end_line) tuples for every
#     top-level function definition found in the file at filepath.
#   - start_line and end_line are 0-indexed and inclusive.
#   - The returned list is ordered by function occurrence within the file.
#   - Returns None when the codegraph backend is unavailable or does not index
#     the file at filepath.
# [SPEC]

# [INFO]
# CodeGraphExtractor.get_function_spans(self, lang_key: str, abs_filepath: str) -> list[tuple[str, int, int]] | None
# Pre-condition:
#   - self is a CodeGraphExtractor instance initialized with a valid codegraph database
#   - lang_key is a non-empty language identifier string
#   - abs_filepath is an absolute path to a source file within the project root
# Post-condition:
#   - Returns None if lang_key unrecognized or file not indexed / contains no definitions
#   - Otherwise returns list of (name, start_idx, end_idx) tuples for every function/method definition in the file
#   - name is class-qualified, suitable for both function FQN tail and path component
#   - start_idx, end_idx are 0-indexed inclusive line numbers, converted from backend 1-indexed representation
#   - List ordered by ascending start_idx
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one Go file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("go", filepath) if cg else None
