def batch_extract(proj_dir: str) -> dict:
    """Return ``{abs_filepath: [(function_id, body)]}`` for Erlang files."""
    return _analysis_or_empty(proj_dir).functions
