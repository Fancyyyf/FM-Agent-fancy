def _collect_project_source_files(proj_dir, submodules=None):
    """Return non-test source files currently present in proj_dir, relative to proj_dir."""
    files = set()
    for rel in _iter_project_source_files(proj_dir, submodules):
        if not _is_test_file(rel):
            files.add(rel)
    return files
