def _normalized_relative_path(proj_dir, path):
    """Return a normalized project-relative key for a source path."""
    absolute_path = path if os.path.isabs(path) else os.path.join(proj_dir, path)
    relative_path = os.path.relpath(absolute_path, proj_dir)
    return os.path.normcase(os.path.normpath(relative_path))
