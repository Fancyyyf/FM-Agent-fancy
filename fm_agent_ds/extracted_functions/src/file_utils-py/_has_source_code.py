def _has_source_code(proj_dir, submodules=None):
    """Check whether proj_dir contains at least one source code file."""
    for _ in _iter_project_source_files(proj_dir, submodules):
        return True
    return False
