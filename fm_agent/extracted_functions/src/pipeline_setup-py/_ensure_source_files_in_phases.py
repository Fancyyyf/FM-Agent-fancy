def _ensure_source_files_in_phases(phases_json, required_source_files):
    """Force-list ``required_source_files`` in phases.json if the agent omitted them.

    The Stage 1 (generate phase.json) agent decides which source files go into phases.json and may
    leave out files that look like tests. When a caller (e.g. the entry pipeline)
    must have a specific file processed regardless, this appends any missing ones
    to the first module of the earliest phase and records them in that module's
    description. No phase is created and nothing is renumbered — the existing phase
    plan is left intact, so the ``phase_NN_types.txt`` files keep their numbering.

    Returns ``{"forced": [...], "augmented": {phase_number: [paths]},
    "augmented_modules": [{"phase": n, "module": name, "added_files": [paths]}]}``.
    ``forced`` is the list of paths that had to be added; ``augmented`` maps the
    (original) number of the phase whose module gained files to those paths, so the
    caller can have that phase's domain-context types file extended; and
    ``augmented_modules`` names the specific module (by original phase number and
    name) that gained the files, so its description can be refreshed too. When
    nothing had to be added all are empty.
    """
    if not required_source_files:
        return {"forced": [], "augmented": {}, "augmented_modules": []}

    with open(phases_json, "r") as f:
        data = json.load(f)

    listed = set()
    for phase in data.get("phases", []):
        for module in phase.get("modules", []):
            for sf in module.get("source_files", []):
                listed.add(sf.replace("\\", "/"))

    missing = [sf for sf in required_source_files if sf.replace("\\", "/") not in listed]
    if not missing:
        return {"forced": [], "augmented": {}, "augmented_modules": []}

    phases = data.get("phases", [])
    if not phases:
        # No phase plan to attach to; create the single phase the files need.
        first_phase = {
            "phase": 1,
            "name": "Entry Points",
            "description": "Entry-point source files.",
            "modules": [],
            "depends_on_phases": [],
        }
        data["phases"] = phases = [first_phase]
    else:
        first_phase = min(phases, key=lambda p: p.get("phase", 0))

    modules = first_phase.setdefault("modules", [])
    if not modules:
        modules.append({
            "name": "entry_points",
            "description": "",
            "source_files": [],
        })
    module = modules[0]
    module.setdefault("source_files", []).extend(missing)
    note = "Includes required entry-point source file(s): " + ", ".join(missing) + "."
    module["description"] = _merge_descriptions(module.get("description", ""), note)

    with open(phases_json, "w") as f:
        json.dump(data, f, indent=2)
    return {
        "forced": missing,
        "augmented": {first_phase.get("phase"): list(missing)},
        "augmented_modules": [{
            "phase": first_phase.get("phase"),
            "module": module.get("name", ""),
            "added_files": list(missing),
        }],
    }
