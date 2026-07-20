# [SPEC]
# Unit: src/pipeline_setup.py
#
# _collapse_phases_to_one(work_dir) -> None
#
# Pre-condition:
#   - work_dir is a string path to a writable directory containing
#     phases.json that conforms to the phases.json schema (a JSON object
#     with a "phases" array; each phase has "phase" (int), "name"
#     (string), "description" (string or null), "modules" (array), and
#     optionally "depends_on_phases" (array of int)).
#   - If work_dir contains spec_prompts/domain_context/, it may contain
#     phase_NN_types.txt files keyed by phase number.
#
# Post-condition:
#   - When phases.json contains no phases (empty "phases" array), the
#     function returns immediately; no files are modified or created.
#   - Otherwise, phases.json is replaced: the "phases" array contains
#     exactly one element — a phase with:
#       * "phase" set to the integer 1.
#       * "name" set to the string "Unified Analysis Phase".
#       * "modules" being the concatenation of every module from every
#         original phase, preserving the ascending phase-number order of
#         original phases and the original module order within each phase.
#       * "description" being the concatenation of every non-empty
#         (after stripping whitespace) description from every original
#         phase, each prefixed by "Phase {N} ({name}): " and joined by
#         "\n\n". If no original phase had a non-empty description,
#         "description" is the empty string.
#       * "depends_on_phases" set to the empty list [].
#   - Domain context files are merged:
#       * Every existing phase_NN_types.txt file is read; their content
#         is concatenated with "\n\n" separators and written to
#         phase_01_types.txt under spec_prompts/domain_context/.
#       * All other phase_*_types.txt files (matching the glob pattern)
#         are deleted.
#       * If no phase_NN_types.txt files existed, phase_01_types.txt is
#         not created and no deletions occur.
#   - Returns None.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
