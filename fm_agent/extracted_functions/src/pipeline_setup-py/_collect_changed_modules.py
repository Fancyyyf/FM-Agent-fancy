def _collect_changed_modules(ensure_changes, *change_sets):
    """Collect the modules whose source-file list changed during post-processing.

    Both ``_ensure_source_files_in_phases`` (which force-adds source files to a
    module), ``_filter_phases_to_submodules`` (which strips out-of-scope files),
    and ``_deduplicate_phases`` (which strips duplicate source files from modules)
    alter which files a module owns, so an affected module's description may no
    longer match. This returns one entry per affected module, giving only its phase
    number and name — the input to ``_update_module_description``. The agent
    re-reads each module's current source files from phases.json itself.

    Dedup no longer renumbers phases, so both sources speak the same phase
    numbering (the one in the freshly written phases.json).
    """
    entries = {}  # (phase, module_name) -> entry
    for changes in change_sets:
        for m in changes.get("modified_modules", []):
            key = (m["phase"], m["module"])
            entries[key] = {"phase": m["phase"], "module": m["module"]}
    for a in ensure_changes.get("augmented_modules", []):
        key = (a["phase"], a["module"])
        entries[key] = {"phase": a["phase"], "module": a["module"]}
    return list(entries.values())
