# [SPEC]
# Unit: src/languages/typescript-py/function_spans.py
#
# function_spans(proj_dir, filepath) -> list[(name, start_idx, end_idx)] | None
#
# Pre-condition:
#   - proj_dir is a path to a project root directory
#   - filepath is a path to a single TypeScript source file residing under proj_dir
#
# Post-condition:
#   - When a codegraph backend initializes successfully from proj_dir AND the backend
#     indexes the TypeScript file at filepath, returns a non‑empty list of
#     (name, start_idx, end_idx) tuples covering every function defined in the file,
#     where name is the function's declared name as a string, and start_idx and end_idx
#     are 0‑indexed inclusive line positions delimiting the function body
#   - When no codegraph backend is available, or the backend exists but does not index
#     the file at filepath, returns None
#   - The order of tuples in the returned list corresponds to the definition order of
#     functions in the source file
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid project directory path
#   Post-condition: Returns a CodeGraphExtractor instance bound to the project when a
#     compatible codegraph backend can be constructed from the project; returns None
#     when no compatible backend is available
# [SPLIT]
# CodeGraphExtractor.get_function_spans(language, filepath) -> list[(name, start_idx, end_idx)] | None
#   Pre-condition: language is a supported language key; filepath is a path to a source
#     file of the given language within the project
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples for every
#     function defined in the file with 0‑indexed inclusive line indices; returns None
#     if the backend does not index the given file
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one TypeScript file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("typescript", filepath) if cg else None
