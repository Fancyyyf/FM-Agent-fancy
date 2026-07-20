# [SPEC]
# Unit: src/pipeline_setup-py/_ensure_source_files_in_phases.py
#
# _ensure_source_files_in_phases(phases_json, required_source_files) -> dict
#
# Pre-condition:
#   - phases_json is a string path to a writable JSON file conforming to the
#     phases.json schema (an object with a "phases" array where each phase has
#     a numeric "phase" key and a "modules" array, and each module has a
#     "source_files" array of relative paths)
#   - required_source_files is None or an iterable of strings
#
# Post-condition:
#   - If required_source_files is None or empty, returns
#     {"forced": [], "augmented": {}, "augmented_modules": []}
#     without modifying the file at phases_json
#   - If required_source_files is non-empty:
#     (a) Every path in required_source_files not already present in any
#         source_files list in phases_json (after normalizing "\" to "/" in
#         both the existing entries and the required files) is appended, in
#         its original form, to the source_files list of the first module of
#         the phase with the smallest "phase" number
#     (b) If no phase exists in phases_json, a single phase numbered 1
#         containing one module named "entry_points" is created to receive
#         all missing source files; the phase has an empty depends_on_phases
#         list
#     (c) If the earliest phase exists but has no modules, a module named
#         "entry_points" with an empty source_files list is created to
#         receive the missing source files
#     (d) The description of the receiving module is appended with a note
#         listing the missing file paths; descriptions are merged without
#         duplication (i.e., if the new note is already a substring of the
#         existing description, no change is made)
#     (e) The file at phases_json is atomically overwritten with the updated
#         JSON, indented with 2 spaces
#     (f) Returns a dict with exactly three keys:
#         - "forced": list of paths (in the same order as they appear in
#           required_source_files) that were not already present and were
#           therefore added
#         - "augmented": dict mapping the source phase number (an integer,
#           as it was when the file was opened, prior to any renumbering) to
#           the list of added paths
#         - "augmented_modules": list of dicts, each containing "phase"
#           (int), "module" (str), and "added_files" (list of str),
#           identifying which specific module received the additions
#   - No path already present in phases_json (after "/" normalization) is
#     duplicated
#   - Existing phase structure — phase numbering, module ordering, module
#     names, description fields of non-receiving modules, and depends_on_phases
#     arrays — is preserved, except for source_files additions and description
#     updates to the single receiving module
# [SPEC]

# [INFO]
# _merge_descriptions(existing, new_note) -> str
#   Pre-condition: existing and new_note are strings
#   Post-condition: Returns existing unchanged when new_note is empty or is
#                    a substring of existing; otherwise returns existing
#                    joined with new_note using a single space separator
# [INFO]

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
