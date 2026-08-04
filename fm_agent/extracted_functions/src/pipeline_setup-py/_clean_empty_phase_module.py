def _clean_empty_phase_module(work_dir):
    """Drop empty modules/phases from phases.json, renumber phases, and keep the
    per-phase domain-context files in sync.

    A module owning no source files, and a phase left with no non-empty modules,
    carry no work for later stages, so both are removed. Surviving phases are then
    renumbered 1..N in their existing order (closing any gaps the removals left),
    and ``depends_on_phases`` references are remapped to the new numbering with
    references to removed phases dropped.

    Because the ``spec_prompts/domain_context/phase_NN_types.txt`` files are keyed
    by phase number, this also deletes the types file of every removed phase and
    renames the types file of every renumbered phase to match its new number.

    Returns ``{"removed_phases": [...], "renumbered": {old: new, ...}}`` describing
    what changed (an unchanged phase maps to itself in ``renumbered``).
    """
    phases_path = os.path.join(work_dir, "phases.json")
    with open(phases_path, "r") as f:
        data = json.load(f)

    original_phases = sorted(data.get("phases", []), key=lambda p: p.get("phase", 0))

    kept = []
    removed_phase_nums = []
    for phase in original_phases:
        modules = [
            m for m in phase.get("modules", [])
            if m.get("source_files")
        ]
        if modules:
            phase["modules"] = modules
            kept.append(phase)
        else:
            removed_phase_nums.append(phase.get("phase"))
            logging.info(
                "Removed empty phase %s ('%s') with no source files",
                phase.get("phase"), phase.get("name", ""),
            )

    # Map each surviving phase's old number to its new (compacted) number.
    renumbered = {}
    for new_num, phase in enumerate(kept, start=1):
        old_num = phase.get("phase")
        if old_num is not None:
            renumbered[old_num] = new_num
        phase["phase"] = new_num

    # Remap dependencies to the new numbering, dropping any that pointed at a
    # removed phase (which no longer exists to depend on).
    for phase in kept:
        deps = phase.get("depends_on_phases")
        if not deps:
            continue
        phase["depends_on_phases"] = sorted(
            {renumbered[d] for d in deps if d in renumbered}
        )

    data["phases"] = kept
    with open(phases_path, "w") as f:
        json.dump(data, f, indent=2)

    _clean_domain_context_files(work_dir, removed_phase_nums, renumbered)
    return {"removed_phases": removed_phase_nums, "renumbered": renumbered}
