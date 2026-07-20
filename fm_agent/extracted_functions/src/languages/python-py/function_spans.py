# [SPEC]
# Unit: src/languages/python-py/function_spans.py
#
# function_spans(proj_dir: str, filepath: str) -> list[tuple[str, int, int]] | None
#
# Pre-condition:
#   - proj_dir is a valid path to a project directory
#   - filepath is a relative or absolute path to a Python source file
#
# Post-condition:
#   - If a codegraph backend is available and indexes the project at proj_dir,
#     returns a list of (name, start_idx, end_idx) tuples, one per function
#     defined in the Python source file at filepath, where start_idx and
#     end_idx are 0-indexed inclusive line numbers delimiting each function body.
#   - Returns None when the codegraph backend cannot be initialized for the
#     project or does not index the given filepath, signaling the caller to
#     fall back to regex-based function extraction for this file.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid path to a project directory
#   Post-condition: Returns a CodeGraphExtractor instance when the project is
#     indexable by codegraph; returns None otherwise.
# [SPLIT]
# CodeGraphExtractor.get_function_spans(language: str, filepath: str) -> list[tuple[str, int, int]] | None
#   Pre-condition: language is a recognized language key (e.g., "python")
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples for
#     each function defined in the source file, with 0-indexed inclusive line
#     indices; returns None if the file is not indexed by this extractor.
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one Python file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("python", filepath) if cg else None
