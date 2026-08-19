def _collect_changed_phases(ensure_changes, *change_sets):
    """Collect the phase numbers whose source-file composition changed during
    post-processing.

    Both ``_ensure_source_files_in_phases`` (which force-adds source files to a
    phase's first module), ``_filter_phases_to_submodules`` (which strips
    out-of-scope files), and ``_deduplicate_phases`` (which strips duplicate source
    files from modules) can change which files a phase owns, so its domain-context
    types file (phase_NN_types.txt) may no longer match. This returns the set of
    affected phase numbers so the caller can have those files regenerated (see
    ``_sync_domain_context``).

    Dedup no longer renumbers phases, so both sources speak the same phase
    numbering (the one in the freshly written phases.json).
    """
    phases = set()
    for phase_num in ensure_changes.get("augmented", {}):
        if phase_num is not None:
            phases.add(phase_num)
    for changes in change_sets:
        for m in changes.get("modified_modules", []):
            phase_num = m.get("phase")
            if phase_num is not None:
                phases.add(phase_num)
    return phases
