# [SPEC]
# Unit: src/languages/python-py/call_edges.py
#
# call_edges(proj_dir: str) -> dict | None
#
# Pre-condition:
#   - proj_dir is a string path to a project root directory.
#
# Post-condition:
#   - Returns a dict when the CodeGraph backend can index the project directory; returns None when the backend is unavailable or the project cannot be indexed.
#   - When a dict is returned, each key identifies a caller function (as a tuple of stem and module identifiers) and each value is a set of callee function identifiers (stems) called by that caller.
#   - The returned call edges cover Python source files (.py) under the project directory.
#   - A callee appears in the returned set only when the CodeGraph backend resolves a call site within the caller's body to that callee.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> object | None
#   Pre-condition: proj_dir is a filesystem path to a project root.
#   Post-condition: Returns a CodeGraphExtractor instance configured for the given project, or a falsy value when the backend is unavailable or the project cannot be indexed.
# [SPLIT]
# cg.get_call_edges(language: str) -> dict | None
#   Pre-condition: language is a valid language key string (e.g., "python").
#   Post-condition: Returns a dict mapping caller identifiers to sets of callee identifiers for the given language, or None when the backend cannot resolve call edges.
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for Python."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("python") if cg else None
