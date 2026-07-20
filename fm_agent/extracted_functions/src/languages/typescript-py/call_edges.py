# [SPEC]
# Unit: src/languages/typescript-py/call_edges.py
#
# call_edges(proj_dir) -> dict | None
#
# Pre-condition:
#   - proj_dir is a path to a project root directory containing TypeScript source files
#
# Post-condition:
#   - When a codegraph backend initializes successfully from proj_dir, returns a dict
#     whose keys are (caller_stem, caller_module) pairs — where caller_stem is a
#     function‑level identifier and caller_module is the containing module identifier —
#     and whose values are sets of callee function stem strings that the corresponding
#     caller directly invokes within the project's TypeScript source
#   - When no codegraph backend is available, returns None
#   - Every callee stem in the returned value sets corresponds to a function reachable
#     from at least one TypeScript source file in the project
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid project directory path
#   Post-condition: Returns a CodeGraphExtractor instance bound to the project when a
#     compatible codegraph backend can be constructed from the project; returns None
#     when no compatible backend is available
# [SPLIT]
# CodeGraphExtractor.get_call_edges(language) -> dict
#   Pre-condition: language is a supported language key recognized by the codegraph backend
#   Post-condition: Returns a dict mapping each caller identity to the set of callee
#     identifiers for all call relationships detected across the project's source files
#     of the given language; the mapping covers both intra-file and cross-file calls
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for TypeScript."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("typescript") if cg else None
