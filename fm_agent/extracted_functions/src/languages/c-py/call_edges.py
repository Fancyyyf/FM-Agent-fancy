# [SPEC]
# Unit: src/languages/c.py
#
# call_edges(proj_dir: str) -> dict | None
#
# Pre-condition:
#   - proj_dir is a string path to an existing project directory
#
# Post-condition:
#   - Returns None when no codegraph backend for the C language can be initialized
#     from proj_dir; this signals the caller to fall back to regex-based call-edge
#     detection for this language
#   - Otherwise returns a dict where each key is a fully-qualified caller function
#     name and each value is a set of fully-qualified callee function names that the
#     caller directly invokes
#   - An empty dict (distinct from None) indicates the backend initialized successfully
#     but found zero call edges
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a path to a project directory
#   Post-condition: Returns an initialized CodeGraphExtractor when the C codegraph
#     backend can be constructed; returns None when the backend is unavailable
# [SPLIT]
# CodeGraphExtractor.get_call_edges("c") -> dict
#   Pre-condition: The instance is a valid, initialized codegraph extractor for C
#   Post-condition: Returns a dict mapping each fully-qualified caller function name
#     to the set of fully-qualified callee function names it directly invokes
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for C."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("c") if cg else None
