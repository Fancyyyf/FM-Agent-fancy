# [SPEC]
# Unit: src/pipeline_setup.py
#
# _post_process_phases(proj_dir, work_dir, required_source_files=None,
#                       submodules=None, one_phase=False) -> bool
#
# Pre-condition:
#   - proj_dir is a string path to an existing project root directory.
#   - work_dir is a string path to a writable fm_agent workspace directory.
#   - phases.json exists under work_dir and conforms to the phases.json
#     schema (a JSON object with a "phases" array; each phase has "phase"
#     (int) and "modules" (array), each module has "source_files" (array)).
#   - required_source_files is None or an iterable of file path strings
#     relative to proj_dir.
#   - submodules is None or a non-empty iterable of subdirectory name
#     strings relative to proj_dir.
#   - one_phase is a truthy/falsy value.
#
# Post-condition:
#   - phases.json is updated in-place (file overwritten) through a sequence
#     of transformations applied in order: ensure required source files →
#     filter submodules → deduplicate → update module descriptions → clean
#     empty phases → optionally collapse to single phase.
#   - When required_source_files is non-None, any listed file not already
#     present in phases.json is inserted; the function prints a message to
#     stdout reporting the count and names of forced files.
#   - When submodules is non-None, any source file whose path does not
#     begin with one of the submodule directory names is removed from
#     phases.json; the function prints a message to stdout reporting the
#     count of removed files.
#   - After deduplication, each source file path appears in exactly one
#     phase. phases.json reflects the deduplication: duplicate entries are
#     removed from all but one phase.
#   - After cleanup, phase numbers are compacted to a contiguous range
#     1..N with no gaps; phases with zero source files are removed.
#   - When one_phase is truthy, all remaining phases are collapsed into a
#     single phase numbered 1 containing all source files.
#   - Returns True if and only if phases.json was structurally modified:
#     files were forced, removed, deduplicated, phases were cleaned
#     (removed or renumbered), or phases were collapsed to one. Returns
#     False if phases.json is unchanged by all transformations.
#   - Messages printed to stdout are informational and do not constitute
#     part of the return value contract.
# [SPEC]

# [INFO]
# _ensure_source_files_in_phases(phases_json_path, required_source_files) -> dict
#   Pre-condition: phases_json_path is a valid path to a writable
#     phases.json; required_source_files is None or an iterable of file
#     path strings.
#   Post-condition: If required_source_files is non-None, ensures every
#     listed file exists in phases.json (inserting if absent); returns a
#     dict with key "forced" mapping to a list of paths that were actually
#     added. If required_source_files is None or empty, returns
#     {"forced": []}.
# [SPLIT]
# _filter_phases_to_submodules(phases_json_path, submodules) -> dict
#   Pre-condition: phases_json_path is a valid path to a writable
#     phases.json; submodules is None or an iterable of subdirectory name
#     strings.
#   Post-condition: When submodules is non-None, removes from phases.json
#     all source files whose path does not begin with any of the submodule
#     directory names. Returns a dict with key "removed" mapping to the
#     count (int) of removed files. When submodules is None, returns
#     {"removed": 0} and phases.json is unchanged.
# [SPLIT]
# _deduplicate_phases(work_dir) -> dict
#   Pre-condition: work_dir is a directory containing phases.json.
#   Post-condition: Ensures each source file path appears in at most one
#     phase in phases.json. Returns a dict with key "modified_modules"
#     mapping to a list of module identifiers from which duplicates were
#     removed.
# [SPLIT]
# _collect_changed_modules(ensure_changes, filter_changes, dedup_changes) -> list
#   Pre-condition: Inputs are the return values from the three preceding
#     transformation steps.
#   Post-condition: Returns a list of module identifiers that were affected
#     by any of the three preceding transformations.
# [SPLIT]
# _update_module_description(proj_dir, work_dir, changed_modules) -> None
#   Pre-condition: proj_dir is the project root; work_dir contains
#     phases.json; changed_modules is an iterable of module identifiers.
#   Post-condition: For each module in changed_modules, its description
#     in phases.json is updated based on the source files it now contains.
# [SPLIT]
# _clean_empty_phase_module(work_dir) -> dict
#   Pre-condition: work_dir is a directory containing phases.json.
#   Post-condition: Phases with zero source files after all module-level
#     cleanup are removed from phases.json. Remaining phase numbers are
#     renumbered to a contiguous 1..N range with no gaps. Returns a dict
#     with keys "removed_phases" (list of int, phase numbers that were
#     removed) and "renumbered" (dict mapping old int phase number to new
#     int phase number for every phase whose number changed).
# [SPLIT]
# _collapse_phases_to_one(work_dir) -> None
#   Pre-condition: work_dir is a directory containing phases.json.
#   Post-condition: All phases in phases.json are collapsed into a single
#     phase numbered 1. All source files from every former phase are merged
#     into phase 1.
# [INFO]

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
