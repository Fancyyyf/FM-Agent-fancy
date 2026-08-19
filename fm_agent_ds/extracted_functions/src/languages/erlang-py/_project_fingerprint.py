def _project_fingerprint(proj_dir: str) -> tuple:
    root = os.path.abspath(proj_dir)
    paths = list(_iter_project_files(root, {".erl", ".hrl"}))
    paths.extend(
        os.path.join(root, name)
        for name in _PROJECT_CONFIG_FILES
        if os.path.isfile(os.path.join(root, name))
    )
    records = []
    for path in sorted(set(paths)):
        stat = os.stat(path)
        records.append((os.path.relpath(path, root), stat.st_size, stat.st_mtime_ns))
    return (tuple(_elp_argv()), tuple(records))
