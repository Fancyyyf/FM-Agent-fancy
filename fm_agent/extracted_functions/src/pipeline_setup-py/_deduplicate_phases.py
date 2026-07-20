# [SPEC]
# Unit: src/pipeline_setup.py
#
# _deduplicate_phases(phases_dir) -> dict
#
# Pre-condition:
#   - phases_dir is a string path to a directory containing a valid
#     phases.json file.
#   - phases.json conforms to the pipeline schema: a JSON object with a
#     "phases" array; each phase has "phase" (int) and "modules" (array);
#     each module has "name" (string) and "source_files" (array of strings).
#   - Each source_files element is a relative file path string from the
#     project root.
#   - The phases.json file is readable and writable by the current process.
#
# Post-condition:
#   - phases.json is overwritten with every source file path appearing in at
#     most one module across all phases.
#   - For any source file path appearing in multiple modules (across the same
#     or different phases), only the first occurrence — in ascending phase
#     number order, then module order within each phase — is preserved; all
#     subsequent occurrences are removed from their respective module's
#     source_files list.
#   - The set of phases and modules is unchanged: no phase or module is
#     removed, even when a module's source_files becomes empty.
#   - Phase numbers, module names, and the ordering of phases/modules within
#     phases.json are preserved.
#   - Returns a dict with the key "modified_modules" mapping to a list of
#     dicts, one per module from which at least one source file was removed.
#     Each module dict contains: "phase" (int — the phase number), "module"
#     (str — the module name), "removed_files" (list of strings — the
#     deduplicated file paths that were removed), and "source_files" (list of
#     strings — the module's remaining source files after deduplication).
#   - Returns {"modified_modules": []} when no duplicate source files exist
#     across modules.
# [SPEC]

# [INFO]
# json.load(f) -> dict
#   Pre-condition: f is a readable file object positioned at the start of a
#     valid JSON document.
#   Post-condition: Returns the parsed JSON as a Python dict whose structure
#     matches the phases.json schema.
# [SPLIT]
# json.dump(data, f, indent=2) -> None
#   Pre-condition: data is a JSON-serializable dict, f is a writable file
#     object.
#   Post-condition: Writes data as indented JSON to f, overwriting any
#     previous content starting at the current file position.
# [SPLIT]
# os.path.join(phases_dir, "phases.json") -> str
#   Pre-condition: phases_dir is a string.
#   Post-condition: Returns a single path string formed by joining phases_dir
#     and "phases.json" with the OS-specific path separator.
# [INFO]

def _deduplicate_phases(phases_dir):
    """Ensure each source file appears in at most one phase; keep the earliest.

    Duplicate source files are stripped from every phase/module after the first
    one that claims them. No phase or module is dropped — not even when it loses
    all of its files; only the ``source_files`` lists shrink, so phase numbering
    and the ``phase_NN_types.txt`` files stay aligned. Returns a change summary
    listing the modules whose file list changed so the caller can refresh their
    descriptions (see ``_update_module_description``).
    """
    phases_path = os.path.join(phases_dir, "phases.json")
    with open(phases_path, "r") as f:
        data = json.load(f)

    seen = set()
    # Modules (phase, module, removed_files) that lost some or all of their source
    # files to deduplication. Their descriptions may still describe files they no
    # longer own, so the caller has the agent rewrite them.
    changed_modules = []
    for phase in sorted(data["phases"], key=lambda p: p["phase"]):
        for module in phase["modules"]:
            original = module["source_files"]
            deduped = []
            for sf in original:
                if sf not in seen:
                    seen.add(sf)
                    deduped.append(sf)
                else:
                    logging.info(
                        "Removed duplicate file '%s' from phase %d module '%s'",
                        sf, phase["phase"], module["name"],
                    )
            module["source_files"] = deduped
            removed_files = [sf for sf in original if sf not in deduped]
            if removed_files:
                # File list changed; record it so its description can be refreshed.
                # The module (and its phase) is kept even if it is now empty.
                changed_modules.append((phase, module, removed_files))

    with open(phases_path, "w") as f:
        json.dump(data, f, indent=2)

    # Report the modules whose file list changed. Phase numbers are unchanged
    # (nothing was dropped or renumbered), so these are the numbers the agent will
    # find in the freshly written phases.json.
    modified_modules = [
        {
            "phase": phase["phase"],
            "module": module.get("name", ""),
            "removed_files": removed_files,
            "source_files": list(module["source_files"]),
        }
        for phase, module, removed_files in changed_modules
    ]
    return {
        "modified_modules": modified_modules,
    }
