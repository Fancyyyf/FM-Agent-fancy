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
