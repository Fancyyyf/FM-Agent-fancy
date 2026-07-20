# [SPEC]
# Unit: src/languages/go-py/call_edges.py
#
# call_edges(proj_dir: str) -> dict | None
#
# Pre-condition:
#   - proj_dir is a non-empty string referencing a project directory.
#
# Post-condition:
#   - Returns a dict whose keys are (stem, module) tuples identifying callers
#     and whose values are sets of callee function stems, representing every
#     caller-to-callee relationship discoverable from Go source files under
#     proj_dir.
#   - Returns None when no codegraph backend is available for the Go language.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for Go."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("go") if cg else None
