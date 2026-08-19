def _post_process_phases(proj_dir, work_dir, required_source_files=None,
                          submodules=None, one_phase=False):
    """Post-process phases.json: ensure required files, filter submodules,
    deduplicate, update descriptions, and clean empty phases before domain
    context generation.

    Returns True if phases.json was modified in a way that requires domain
    context regeneration (source files added/removed or phases renumbered).
    """
    phases_json = os.path.join(work_dir, "phases.json")

    ensure_changes = _ensure_source_files_in_phases(phases_json, required_source_files)
    forced = ensure_changes.get("forced", [])
    if forced:
        print(f"[Pipeline] Forced {len(forced)} required source file(s) into phases.json: {', '.join(forced)}")

    filter_changes = _filter_phases_to_submodules(phases_json, submodules)
    if submodules:
        print(f"[Pipeline] Submodule scope: {', '.join(submodules)}")
        removed = filter_changes.get("removed", 0)
        if removed:
            print(f"[Pipeline] Removed {removed} out-of-scope source file(s) from phases.json.")

    dedup_changes = _deduplicate_phases(work_dir)

    changed_modules = _collect_changed_modules(
        ensure_changes, filter_changes, dedup_changes
    )
    _update_module_description(proj_dir, work_dir, changed_modules)

    cleanup_result = _clean_empty_phase_module(work_dir)

    if one_phase:
        _collapse_phases_to_one(work_dir)

    phases_modified = bool(
        forced
        or filter_changes.get("removed", 0)
        or dedup_changes.get("modified_modules")
        or cleanup_result.get("removed_phases")
        or any(
            old != new
            for old, new in cleanup_result.get("renumbered", {}).items()
        )
        or one_phase
    )
    return phases_modified
