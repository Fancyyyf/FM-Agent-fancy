def _iter_project_files(proj_dir: str, suffixes: set[str]):
    for root, dirs, files in os.walk(proj_dir):
        dirs[:] = [directory for directory in dirs if directory.lower() not in _SKIP_DIRS]
        for filename in files:
            if Path(filename).suffix.lower() in suffixes:
                yield os.path.abspath(os.path.join(root, filename))
