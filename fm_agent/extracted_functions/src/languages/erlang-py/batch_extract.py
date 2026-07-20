# [SPEC]
# Unit: src/languages/erlang-py/batch_extract.py
#
# batch_extract(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a valid filesystem path to a project directory
#
# Post-condition:
#   - Returns a mapping from absolute .erl file paths to lists of (function_identifier, source_text) tuples
#   - Each function_identifier is a string uniquely naming a top-level Erlang function within its source module
#   - Each source_text is the complete function body as found in the corresponding file
#   - If Erlang-specific analysis is unavailable for the project at proj_dir, returns an empty dict
# [SPEC]

# [INFO]
# _analysis_or_empty(root: str) -> object
#   Pre-condition: root is a filesystem path
#   Post-condition: Returns an analysis object whose .functions attribute yields the extracted-function mapping; returns an object whose .functions is an empty dict when analysis is unavailable for the given root
# [INFO]

def batch_extract(proj_dir: str) -> dict:
    """Return ``{abs_filepath: [(function_id, body)]}`` for Erlang files."""
    return _analysis_or_empty(proj_dir).functions
