# [SPEC]
# Unit: src/languages/erlang-py/call_edges.py
#
# call_edges(proj_dir: str) -> dict
#
# Pre-condition:
#   - proj_dir is a valid filesystem path to a project directory
#
# Post-condition:
#   - Returns a mapping from caller fully-qualified names to sets of callee fully-qualified names
#   - FQNs follow the format: path::components::delimited::by::double::colons, where the last component is the function name
#   - Each callee in the returned graph is a function that exists within the analyzed Erlang project
#   - If Erlang-specific analysis is unavailable for the project at proj_dir, returns an empty dict
# [SPEC]

# [INFO]
# _callgraph_project_root(proj_dir: str) -> str
#   Pre-condition: proj_dir is a filesystem path to a project directory
#   Post-condition: Returns the effective root directory used for call-graph analysis, which may differ from proj_dir when the project root is a subdirectory of proj_dir
# [SPLIT]
# _analysis_or_empty(root: str) -> object
#   Pre-condition: root is a filesystem path
#   Post-condition: Returns an analysis object whose .edges attribute yields the caller-to-callees mapping; returns an object whose .edges is an empty dict when analysis is unavailable for the given root
# [INFO]

def call_edges(proj_dir: str) -> dict:
    """Return module-qualified Erlang call edges in registry format."""
    return _analysis_or_empty(_callgraph_project_root(proj_dir)).edges
