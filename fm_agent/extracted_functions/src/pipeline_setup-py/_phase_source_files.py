def _phase_source_files(phases_json):
    """Return a mapping of phase number -> its combined source files in phases.json.

    Files from all of a phase's modules are merged, so an empty list means the
    phase currently owns no source files. A missing or malformed phases.json yields
    an empty mapping.
    """
    try:
        with open(phases_json, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    result = {}
    for phase in data.get("phases", []):
        phase_num = phase.get("phase")
        if phase_num is None:
            continue
        files = result.setdefault(phase_num, [])
        for module in phase.get("modules", []):
            files.extend(module.get("source_files", []))
    return result
