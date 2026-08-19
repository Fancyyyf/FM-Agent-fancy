def call_edges(proj_dir: str) -> dict:
    """Return module-qualified Erlang call edges in registry format."""
    return _analysis_or_empty(_callgraph_project_root(proj_dir)).edges
