def function_spans(proj_dir: str, filepath: str):
    """Return ELP function ranges as 0-based inclusive source-line spans."""
    path = os.path.abspath(filepath)
    return _analysis_or_empty(proj_dir).spans.get(path)
