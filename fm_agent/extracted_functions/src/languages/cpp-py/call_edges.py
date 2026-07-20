# [SPEC]
# Unit: src/languages/cpp-py/call_edges.py
#
# call_edges(proj_dir: str) -> dict | None
#
# Pre-condition:
#   - proj_dir is a valid path to a project directory on the filesystem
#
# Post-condition:
#   - Returns None when a codegraph backend is unavailable for the given project
#   - Otherwise returns a dict in which each key is a (function_name, module_name) pair identifying a C++ function within the project, and each associated value is a set of function-name strings identifying the C++ functions directly called by that caller
#   - The returned dict covers all C++ source files in the project that the codegraph backend indexes
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str)
#   Pre-condition: proj_dir is a valid path to a project directory on the filesystem
#   Post-condition: Returns a CodeGraphExtractor instance for the project if the codegraph backend is available, or a falsy value otherwise
# [SPLIT]
# cg.get_call_edges(lang_key: str) where lang_key="cpp"
#   Pre-condition: cg is a valid CodeGraphExtractor instance bound to the project
#   Post-condition: Returns a dict mapping caller (function_name, module_name) pairs to sets of callee function-name strings for the specified language
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for C++."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("cpp") if cg else None
