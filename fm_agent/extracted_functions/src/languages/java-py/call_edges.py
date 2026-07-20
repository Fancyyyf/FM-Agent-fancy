# [SPEC]
# Unit: fm_agent/extracted_functions/src/languages/java-py/call_edges.py
#
# call_edges(proj_dir: str) -> dict | None
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path to a valid project directory
#
# Post-condition:
#   - When a Java code graph backend is available, returns a dict mapping
#     (caller_stem: str, caller_module: str) tuples to sets of callee stems,
#     representing all call-graph edges for Java functions in the project
#   - When the Java backend is unavailable, returns None
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a valid project directory path
#   Post-condition: Returns a CodeGraphExtractor instance initialized for the project,
#     or None when the Java code graph backend cannot be initialized
# [SPLIT]
# cg.get_call_edges("java") -> dict
#   Pre-condition: cg is a valid CodeGraphExtractor instance
#   Post-condition: Returns a dict mapping (caller_stem: str, caller_module: str) tuples
#     to sets of callee stems for all Java call-graph edges in the project
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for Java."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("java") if cg else None
