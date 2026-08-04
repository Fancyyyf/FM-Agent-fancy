def _collapse_phases_to_one(work_dir):
    """Merge every planned module and its type context into phase 1."""
    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path) as f:
        data = json.load(f)
    phases = sorted(data.get("phases", []), key=lambda phase: phase.get("phase", 0))
    if not phases:
        return

    merged_description = "\n\n".join(
        f"Phase {phase['phase']} ({phase['name']}): {phase_description}"
        for phase in phases
        if (phase_description := (phase.get("description") or "").strip())
    )
    first = phases[0]
    first["name"] = "Unified Analysis Phase"
    first["description"] = merged_description
    first["modules"] = [
        module
        for phase in phases
        for module in phase.get("modules", [])
    ]
    first["depends_on_phases"] = []
    data["phases"] = [first]
    with open(phases_path, "w") as f:
        json.dump(data, f, indent=2)

    domain_dir = os.path.join(work_dir, "spec_prompts", "domain_context")
    merged_types_path = os.path.join(domain_dir, "phase_01_types.txt")
    type_context = []
    for phase in phases:
        types_path = os.path.join(domain_dir, f"phase_{phase['phase']:02d}_types.txt")
        if os.path.isfile(types_path):
            with open(types_path) as f:
                type_context.append(f.read().strip())
    if type_context:
        with open(merged_types_path, "w") as f:
            f.write("\n\n".join(type_context) + "\n")
        for types_path in glob.glob(os.path.join(domain_dir, "phase_*_types.txt")):
            if types_path != merged_types_path:
                os.remove(types_path)
