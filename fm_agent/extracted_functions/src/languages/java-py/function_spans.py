# [SPEC]
# Unit: src/languages/java-py/function_spans.py
#
# function_spans(proj_dir, filepath)
#
# Pre-condition:
#   - proj_dir is a string path to a valid project root directory containing Java source files.
#   - filepath is a string path to a Java source file (.java) located within proj_dir.
#
# Post-condition:
#   - If the codegraph backend is available and indexes the given Java file, returns a list of
#     (name, start_idx, end_idx) tuples, one per function definition found in the file, ordered
#     by appearance in the source. Each tuple contains the function name as a string and
#     0-indexed inclusive line indices delimiting the function body.
#   - If the codegraph backend is unavailable or does not index the file, returns None,
#     signalling that the caller must fall back to regex-based extraction.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor or None
#   Pre-condition: proj_dir is a valid filesystem path to a project directory.
#   Post-condition: Returns a CodeGraphExtractor instance with a loaded code graph for the
#     project, or None when the backend cannot be initialized for the given directory.
# [SPLIT]
# CodeGraphExtractor.get_function_spans(language, filepath) -> list of (str, int, int) or None
#   Pre-condition: language is a non-empty language key string; filepath is an absolute
#     filesystem path to a source file residing under the project root.
#   Post-condition: Returns a list of (name, start_idx, end_idx) tuples for each function
#     definition found in the file, ordered by ascending start_idx (0-indexed inclusive).
#     Returns None when the language is not recognized, the file is not indexed, the file
#     contains no function definitions, or the file path cannot be resolved, signalling the
#     caller to fall back to regex-based extraction.
# [INFO]

def function_spans(proj_dir: str, filepath: str):
    """Return [(name, start_idx, end_idx)] for one Java file, or None.

    Line indices are 0-indexed and inclusive. None means codegraph is
    unavailable or does not index the file, so the caller falls back to the
    regex extractor.
    """
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_function_spans("java", filepath) if cg else None
