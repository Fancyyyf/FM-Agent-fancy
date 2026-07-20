# [SPEC]
# Unit: src/languages/erlang-py/_analyze_project.py
#
# _analyze_project(proj_dir: str) -> ErlangAnalysis
#
# Pre-condition:
#   - proj_dir is a non-empty string representing a filesystem path to an existing,
#     accessible project directory
#
# Post-condition:
#   - Returns an ErlangAnalysis object whose .functions attribute is a dict mapping
#     absolute .erl file paths to lists of (func_name, source_text) tuples, whose
#     .edges attribute is a dict mapping caller FQNs to sets of callee FQNs, and
#     whose .spans attribute is a dict mapping absolute file paths to lists of
#     (func_name, start_line, end_line) tuples
#   - The returned ErlangAnalysis is populated from the Erlang Language Platform
#     analysis of the project at proj_dir
#   - Raises an exception when the ELP backend is unavailable or analysis cannot
#     complete (including process failure or inaccessible project)
# [SPEC]

# [INFO]
# _project_fingerprint(root: str) -> Any
#   Pre-condition: root is an absolute path to a project directory
#   Post-condition: Returns a content-based fingerprint that changes if and only if
#     the project's content relevant to Erlang analysis has changed at root
# [SPLIT]
# _analyze_project_uncached(root: str) -> ErlangAnalysis
#   Pre-condition: root is an absolute path to a project directory
#   Post-condition: Returns an ErlangAnalysis populated with functions, edges, and
#     spans extracted by ELP for the project at root; raises an exception when the
#     ELP backend is unavailable or analysis cannot complete
# [SPLIT]
# _persist_analysis(root: str, fingerprint: Any, analysis: ErlangAnalysis)
#   Pre-condition: root is an absolute path, fingerprint is the project fingerprint,
#     analysis is a populated ErlangAnalysis
#   Post-condition: Writes the analysis to persistent storage keyed by root and
#     fingerprint; raises OSError when persistence fails
# [INFO]

def _analyze_project(proj_dir: str) -> ErlangAnalysis:
    root = os.path.abspath(proj_dir)
    fingerprint = _project_fingerprint(root)
    with _CACHE_LOCK:
        cached = _CACHE.get(root)
        if cached and cached[0] == fingerprint:
            return cached[1]

    analysis = _analyze_project_uncached(root)
    try:
        _persist_analysis(root, fingerprint, analysis)
    except OSError as exc:
        logging.warning("Unable to persist ELP Erlang call graph for %s: %s", root, exc)
    with _CACHE_LOCK:
        _CACHE[root] = (fingerprint, analysis)
    return analysis
