# [SPEC]
# Unit: src/pipeline_setup-py/_filter_phases_to_submodules.py
#
# _filter_phases_to_submodules(phases_json, submodules) -> dict
#
# Pre-condition:
#   - phases_json is a string path to an existing phases.json file whose parent
#     directory is writable and whose content conforms to the phases.json schema
#     (a JSON object with a "phases" array; each phase has "phase" (int) and
#     "modules" (array); each module has "source_files" (array of strings)).
#   - submodules is None or a non-empty iterable of subdirectory name strings
#     relative to the project root.
#
# Post-condition:
#   - When submodules is None or empty, phases.json is unchanged on disk and
#     the function returns {"removed": 0, "modified_modules": []}.
#   - When submodules is non-empty, every source_file path in every module of
#     every phase is classified: paths that begin with any of the submodule
#     directory names are retained; all other paths are removed from their
#     module.
#   - Returns a dict with two keys: "removed" maps to the total count (int) of
#     removed source_file entries; "modified_modules" maps to a list of
#     objects, one per module from which at least one file was removed, each
#     containing the phase number, module name, the list of removed file paths,
#     and the list of retained file paths.
#   - When at least one source_file is removed, the file at phases_json is
#     overwritten with the filtered phases.json content; when no source_file is
#     removed, the file at phases_json is not modified.
# [SPEC]

# [INFO]
# _is_under_submodules(source_file, submodules) -> bool
#   Pre-condition: source_file is a file path string; submodules is a non-empty
#     iterable of subdirectory name strings.
#   Post-condition: Returns True when source_file begins with any of the
#     submodule directory name strings; returns False when source_file does not
#     begin with any submodule directory name string.
# [INFO]

def _filter_phases_to_submodules(phases_json, submodules):
    """Remove out-of-scope source files from phases.json without renumbering."""
    if not submodules:
        return {"removed": 0, "modified_modules": []}

    with open(phases_json, "r") as f:
        data = json.load(f)

    removed_total = 0
    modified_modules = []
    for phase in sorted(data.get("phases", []), key=lambda p: p.get("phase", 0)):
        for module in phase.get("modules", []):
            original = list(module.get("source_files", []))
            kept = []
            removed = []
            for source_file in original:
                if _is_under_submodules(source_file, submodules):
                    kept.append(source_file)
                else:
                    removed.append(source_file)
            if not removed:
                continue
            module["source_files"] = kept
            removed_total += len(removed)
            modified_modules.append({
                "phase": phase.get("phase"),
                "module": module.get("name", ""),
                "removed_files": removed,
                "source_files": list(kept),
            })

    if modified_modules:
        with open(phases_json, "w") as f:
            json.dump(data, f, indent=2)

    return {"removed": removed_total, "modified_modules": modified_modules}
