# [SPEC]
# Unit: src/languages/javascript-py/call_edges.py
#
# call_edges(proj_dir: str) -> dict | None
#
# Pre-condition:
#   - proj_dir is a path to an existing project directory containing JavaScript source files.
#
# Post-condition:
#   - Returns None when the codegraph backend cannot be constructed for the project.
#   - Otherwise returns a dict whose keys are caller identifiers and whose values are sets of
#     callee identifier stems that the caller statically references.
#   - Every value set contains only non-empty string stems.
#   - The returned dict includes every static call relationship detected among JavaScript
#     source files within the project.
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir: str) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid path to the project root.
#   Post-condition: Returns a configured codegraph extractor instance, or None if the
#     codegraph backend is not available or cannot index the project.
# [SPLIT]
# cg.get_call_edges(language_key: str) -> dict
#   Pre-condition: cg is a successfully constructed CodeGraphExtractor; language_key is a
#     recognized language identifier.
#   Post-condition: Returns a dict mapping each detected caller to the set of callees it
#     statically references within source files for the given language.
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for JavaScript."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("javascript") if cg else None
