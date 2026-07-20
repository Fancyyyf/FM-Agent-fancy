# [SPEC]
# Unit: src/pipeline_setup.py
#
# _collect_changed_modules(ensure_changes, *change_sets) -> list
#
# Pre-condition:
#   - ensure_changes is a dict that may contain an "augmented_modules" key
#     whose value is a list of dicts, each with at least "phase" and "module"
#     keys.
#   - Each positional argument in change_sets is a dict that may contain a
#     "modified_modules" key whose value is a list of dicts, each with at
#     least "phase" and "module" keys.
#
# Post-condition:
#   - Returns a list of dicts, each containing "phase" and "module" keys,
#     with no duplicate (phase, module) pairs.
#   - The set of (phase, module) pairs in the result is exactly the union of
#     all pairs from every change_set's "modified_modules" list (in the order
#     the change_sets arguments are given) and from
#     ensure_changes["augmented_modules"].
#   - When a (phase, module) pair appears in multiple inputs, only the first
#     occurrence is retained in the result.
#   - The order of entries in the result is the order of first appearance
#     across the inputs: change_sets in positional order, then
#     ensure_changes.
#   - Returns an empty list when none of the inputs contain
#     "modified_modules" / "augmented_modules" keys, or when those keys are
#     absent or map to empty lists.
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

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
