def _normalize_submodules(proj_dir, submodules):
    """Return validated project-relative submodule directories."""
    if not submodules:
        return []

    proj_dir = os.path.abspath(proj_dir)
    normalized = []
    seen = set()
    for raw in submodules:
        value = (raw or "").strip()
        if not value:
            continue
        candidate = value if os.path.isabs(value) else os.path.join(proj_dir, value)
        candidate = os.path.abspath(candidate)
        try:
            inside_project = os.path.commonpath([proj_dir, candidate]) == proj_dir
        except ValueError:
            inside_project = False
        if not inside_project or candidate == proj_dir:
            raise ValueError(
                f"--submodule must name subdirectories inside proj_dir, got: {raw}"
            )
        if not os.path.isdir(candidate):
            raise ValueError(f"--submodule path is not a directory: {raw}")

        rel = os.path.relpath(candidate, proj_dir).replace(os.sep, "/")
        if rel not in seen:
            normalized.append(rel)
            seen.add(rel)

    collapsed = []
    for rel in sorted(normalized, key=lambda path: (path.count("/"), path)):
        if not collapsed or not _is_under_submodules(rel, collapsed):
            collapsed.append(rel)
    return collapsed
