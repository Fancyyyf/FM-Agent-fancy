def _get_all_phase_files(phases_data, input_dir):
    """Return extracted function files reachable from all phases in phases.json."""
    phase_files = []
    seen = set()
    for phase_info in phases_data.get("phases", []):
        phase_num = phase_info.get("phase")
        if phase_num is None:
            continue
        for rel in _get_phase_files(phases_data, phase_num, input_dir):
            if rel not in seen:
                seen.add(rel)
                phase_files.append(rel)
    return phase_files
