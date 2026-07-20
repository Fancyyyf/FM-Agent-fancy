# [SPEC]
# Unit: src/languages/rust-py/call_edges.py
#
# call_edges(proj_dir) -> dict | None
#
# Pre-condition:
#   - proj_dir is a string representing a filesystem path to a project directory
#
# Post-condition:
#   - When the codegraph backend initializes successfully, returns a dictionary whose keys are
#     2-tuples of (caller_stem: str, caller_module: str) and whose values are sets of callee_stem
#     strings, describing caller-callee relationships among Rust source files within the project
#   - Each key-value pair maps one identified caller entity to the set of callee stems it directly
#     invokes
#   - Returns None when no Rust codegraph backend is available for the given project
# [SPEC]

# [INFO]
# CodeGraphExtractor.from_proj_dir(proj_dir) -> CodeGraphExtractor | None
#   Pre-condition: proj_dir is a string representing a valid project directory path
#   Post-condition: Returns a configured CodeGraphExtractor instance for the project when the
#     backend initializes successfully; returns None when the backend cannot be initialized
# [SPLIT]
# CodeGraphExtractor.get_call_edges(lang) -> dict
#   Pre-condition: lang is a recognized language key string
#   Post-condition: Returns a dictionary mapping (caller_stem, caller_module) tuples to sets of
#     callee_stems describing all direct caller-callee relationships for source files of the given
#     language
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return {(caller_stem, caller_module): {callee_stems}} for Rust."""
    cg = CodeGraphExtractor.from_proj_dir(proj_dir)
    return cg.get_call_edges("rust") if cg else None
