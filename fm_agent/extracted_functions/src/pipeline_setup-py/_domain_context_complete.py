def _domain_context_complete(work_dir):
    """Return True only if all domain context files exist and match the phases in phases.json."""
    phases_path = os.path.join(work_dir, "phases.json")
    if not _json_file_is_valid(phases_path):
        return False

    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    if not os.path.exists(os.path.join(domain_dir, "engine_overview.txt")):
        return False

    try:
        with open(phases_path, "r") as f:
            phases_data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False

    for phase in phases_data.get("phases", []):
        phase_num = phase.get("phase")
        if phase_num is None:
            return False
        types_path = os.path.join(domain_dir, f"phase_{phase_num:02d}_types.txt")
        if not os.path.exists(types_path):
            return False

    return True
