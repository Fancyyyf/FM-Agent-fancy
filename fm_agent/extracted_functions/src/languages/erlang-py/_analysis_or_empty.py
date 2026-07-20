# [SPEC]
# Unit: src/languages/erlang-py/_analysis_or_empty.py
#
# _analysis_or_empty(proj_dir: str) -> ErlangAnalysis
#
# Pre-condition:
#   - proj_dir is a non-empty string representing a filesystem path to a project directory
#
# Post-condition:
#   - When Erlang analysis succeeds for the project at proj_dir, returns an ErlangAnalysis
#     object whose .functions attribute is a dict mapping absolute .erl file paths to lists
#     of (func_name, source_text) tuples, whose .edges attribute is a dict mapping caller
#     FQNs to sets of callee FQNs, and whose .spans attribute is a dict mapping absolute
#     file paths to lists of (func_name, start_line, end_line) tuples
#   - When any exception occurs during analysis (including backend unavailability, project
#     not accessible, or ELP process failure), logs a warning with the project directory
#     path and exception details, then returns an ErlangAnalysis object whose .functions,
#     .edges, and .spans attributes are all empty dicts
#   - The returned ErlangAnalysis is never None
# [SPEC]

# [INFO]
# _analyze_project(proj_dir: str) -> ErlangAnalysis
#   Pre-condition: proj_dir is a string path to a project directory
#   Post-condition: Returns an ErlangAnalysis object populated with the functions, edges,
#     and spans extracted by the Erlang Language Platform for the project at proj_dir;
#     raises an exception when the ELP backend is unavailable or analysis cannot complete
# [SPLIT]
# ErlangAnalysis(functions: dict, edges: dict) -> ErlangAnalysis
#   Pre-condition: functions and edges are dicts conforming to the expected mapping types
#   Post-condition: Returns a new ErlangAnalysis instance with the given functions and
#     edges attributes; spans defaults to an empty dict when not explicitly provided
# [INFO]

def _analysis_or_empty(proj_dir: str) -> ErlangAnalysis:
    try:
        return _analyze_project(proj_dir)
    except Exception as exc:
        logging.warning("ELP Erlang analysis unavailable for %s: %s", proj_dir, exc)
        return ErlangAnalysis(functions={}, edges={})
