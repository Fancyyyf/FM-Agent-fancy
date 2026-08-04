def _remove_stale_extracted(proj_dir, modified_functions):
    """
    Reconcile the extracted-function tree against what codegraph now produces,
    deleting any file that no longer corresponds to a current source function and
    pruning emptied directories.

    We reconcile every source file in the current phases.json plus any file
    reported changed or deleted — not only files whose regex-visible function names
    changed. A qualifier-only edit (e.g. renaming a C++ namespace around an
    otherwise identical ``void foo(){...}``) moves the extracted file to a new
    qualified directory without changing the regex name or body, so the old
    qualified file would otherwise linger as a stale, orphaned spec. Reconciling by
    path rather than by (class-less) name handles it.
    """
    srcs = set(modified_functions)  # abs paths; includes deleted source files
    try:
        phases_data = _load_phases(os.path.join(proj_dir, "fm_agent"))
        for phase in phases_data.get("phases", []):
            for module in phase.get("modules", []):
                for rel in module.get("source_files", []):
                    srcs.add(os.path.abspath(os.path.join(proj_dir, rel)))
    except (OSError, ValueError, KeyError):
        pass
    for abs_src in srcs:
        _reconcile_extracted_dir(proj_dir, abs_src)
