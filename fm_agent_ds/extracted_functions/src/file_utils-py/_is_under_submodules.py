def _is_under_submodules(rel_path, submodules):
    """Return whether rel_path is inside one of the selected submodule dirs."""
    if not submodules:
        return True
    norm = rel_path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return any(norm == sub or norm.startswith(sub + "/") for sub in submodules)
