# [SPEC]
# Unit: fm_agent/extracted_functions/src/incremental_reasoner-py/_project_call_graph.py
#
# _project_call_graph(work_dir, extra_call_edges=None) -> tuple
#
# Pre-condition:
#   - work_dir is a path to a project directory whose fm_agent/ subdirectory contains
#     phases.json with a "phases" key whose value is a list of phase objects, each
#     containing at least a "modules" key
#   - extra_call_edges is None or an object providing supplemental caller→callee edges
#     keyed by callee FQN and caller FQN, with optional edge labels
#
# Post-condition:
#   - Returns a 4-tuple (callees_map, callers_map, file_map, edge_aliases_map)
#   - callees_map is a dict mapping every FQN that appears in any phase of phases.json
#     to the set of FQNs it directly calls, spanning all phases and including any
#     supplemental edges from extra_call_edges
#   - callers_map is a dict mapping every FQN to the set of FQNs that directly call it —
#     the exact inverse of callees_map (FQN A ∈ callees_map[B] ⇔ B ∈ callers_map[A])
#   - file_map is a dict mapping every FQN to the absolute filesystem path of the
#     extracted-function file that defines it
#   - edge_aliases_map maps callee FQN → caller FQN → supplemental edge labels as
#     provided by extra_call_edges; for FQN pairs without supplemental labels the
#     inner mapping is absent or empty
#   - Each distinct extracted-function file path contributes its functions exactly once,
#     regardless of how many phases reference that file (deduplication across phases)
#   - All four returned mappings are derived from the same underlying call-graph
#     computation: callees_map, callers_map, and file_map are mutually consistent
#     (every FQN key in any of them appears in all of them)
# [SPEC]

# [INFO]
# _load_phases(work_dir) -> dict
#   Pre-condition: work_dir is a directory containing fm_agent/phases.json
#   Post-condition: returns a dict whose "phases" key maps to a list of phase objects,
#     each containing at least a "modules" key with a list of module objects
# [SPLIT]
# _collect_phase_files(work_dir, phase) -> iterable of (str, str)
#   Pre-condition: work_dir is the project directory; phase is a phase object from
#     phases.json containing a "modules" list
#   Post-condition: yields (absolute_file_path, module_name) tuples for every
#     extracted-function file belonging to this phase, where module_name identifies
#     the phase-level module that owns the file
# [SPLIT]
# _build_call_graph(all_files, work_dir, extra_call_edges=None) -> tuple
#   Pre-condition: all_files is a non-empty list of (absolute_file_path, module_name)
#     pairs; extra_call_edges may provide supplemental caller→callee edges
#   Post-condition: returns a 6-tuple (callees_map, callers_map, all_callees_set,
#     file_map, module_map, edge_aliases_map) representing the complete intra-phase
#     and cross-phase call graph across all provided files, where callees_map and
#     callers_map are mutually inverse and file_map maps each FQN to its absolute
#     extracted-function file path
# [INFO]

def _project_call_graph(work_dir, extra_call_edges=None):
    """
    Build the project-wide call graph (keyed by FQN) over every extracted function.

    Treats all extracted functions across every phase in phases.json as one graph, so
    callee/caller edges span the whole project. Returns (callees_map, callers_map,
    file_map, edge_aliases_map): callees_map maps each FQN to the set of FQNs it calls
    directly, callers_map the inverse (each FQN to the FQNs that call it directly),
    file_map maps each FQN to the absolute path of its extracted-function file, and
    edge_aliases_map maps callee -> caller -> supplemental edge labels.
    """
    phases = _load_phases(work_dir)
    all_files = []
    seen = set()
    for phase in phases.get("phases", []):
        for fpath, module_name in _collect_phase_files(work_dir, phase):
            if fpath not in seen:
                seen.add(fpath)
                all_files.append((fpath, module_name))

    (
        callees_map,
        callers_map,
        _all_callees,
        file_map,
        _modmap,
        edge_aliases_map,
    ) = _build_call_graph(
        all_files,
        work_dir,
        extra_call_edges=extra_call_edges,
    )
    return callees_map, callers_map, file_map, edge_aliases_map
