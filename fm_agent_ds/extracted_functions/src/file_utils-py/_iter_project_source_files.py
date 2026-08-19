def _iter_project_source_files(proj_dir, submodules=None):
    """Yield project-relative source file paths, optionally limited to submodules."""
    from src.extract import EXT_TO_LANG  # local import to avoid circular import
    source_exts = set(EXT_TO_LANG.keys())
    scan_roots = [proj_dir]
    if submodules:
        scan_roots = [
            os.path.join(proj_dir, submodule.replace("/", os.sep))
            for submodule in submodules
        ]

    for scan_root in scan_roots:
        for root, dirs, files in os.walk(scan_root):
            # Skip hidden dirs and common non-source dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                       {'node_modules', '__pycache__', 'venv', '.venv', 'fm_agent'}]
            for fname in files:
                ext = fname.rsplit('.', 1)[-1] if '.' in fname else ''
                if ext not in source_exts:
                    continue
                rel = os.path.relpath(os.path.join(root, fname), proj_dir)
                rel = rel.replace(os.sep, "/")
                if _is_under_submodules(rel, submodules):
                    yield rel
