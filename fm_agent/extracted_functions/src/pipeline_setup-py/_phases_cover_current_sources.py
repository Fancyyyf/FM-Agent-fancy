def _phases_cover_current_sources(phases_json, proj_dir, submodules=None):
    """Return whether phases.json is valid for the current source-file set."""
    try:
        with open(phases_json, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False

    listed = set()
    for phase in data.get("phases", []):
        for module in phase.get("modules", []):
            for source_file in module.get("source_files", []):
                listed.add(source_file.replace("\\", "/"))

    if not listed:
        return False
    if submodules and any(not _is_under_submodules(sf, submodules) for sf in listed):
        return False
    if any(not os.path.exists(os.path.join(proj_dir, sf)) for sf in listed):
        return False
    return _collect_project_source_files(proj_dir, submodules).issubset(listed)
