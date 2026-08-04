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
