# [SPEC]
# Unit: src/pipeline_setup.py
#
# _clean_empty_phase_module(work_dir) -> dict
#
# Pre-condition:
#   - work_dir is a string path to a writable directory containing
#     phases.json that conforms to the phases.json schema (a JSON object
#     with a "phases" array; each phase has "phase" (int), "modules"
#     (array), and optionally "depends_on_phases" (array of int)).
#   - If work_dir contains spec_prompts/domain_context/, it may contain
#     phase_NN_types.txt files keyed by phase number.
#
# Post-condition:
#   - phases.json is modified in-place (file overwritten):
#       * Every module whose source_files array is absent, null, or empty
#         is removed from its phase.
#       * Every phase left with no modules (empty modules array after
#         pruning) is removed from the phases array.
#       * Surviving phases are renumbered to a contiguous 1..N range
#         in ascending order of their original phase numbers (no gaps).
#       * For each surviving phase, every element in depends_on_phases
#         is remapped to the new phase number; references to removed
#         phases are dropped. The resulting depends_on_phases array is
#         sorted in ascending order and contains no duplicates.
#   - Domain context files are synced:
#       * For every removed phase number, the corresponding
#         phase_NN_types.txt file is deleted.
#       * For every phase that was renumbered (old != new), the
#         corresponding types file is renamed from phase_<old>_types.txt
#         to phase_<new>_types.txt.
#   - Returns a dict with two keys:
#       * "removed_phases": list of int, the original phase numbers that
#         were removed (empty list if none were removed).
#       * "renumbered": dict mapping int (old phase number) to int (new
#         phase number) for every phase present in the original
#         phases.json, including phases whose number did not change
#         (mapped to themselves).
#   - If no phases were removed and no phase numbers changed, the return
#     dict has "removed_phases": [] and "renumbered" where every key
#     equals its value.
# [SPEC]

# [INFO]
# _clean_domain_context_files(work_dir, removed_phase_nums, renumbered) -> None
#   Pre-condition: work_dir is a directory containing
#     spec_prompts/domain_context/ with phase_NN_types.txt files.
#     removed_phase_nums is a list of int phase numbers.
#     renumbered is a dict mapping int (old) to int (new).
#   Post-condition: For each phase number in removed_phase_nums, the
#     phase_NN_types.txt file is deleted if it exists. For each
#     (old, new) pair in renumbered where old != new, the file
#     phase_<old>_types.txt is renamed to phase_<new>_types.txt.
# [INFO]

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
