def _select_functions_by_source(proj_dir, entry_func, end_funcs, extra_call_edges=None):
    """Select the functions reachable from entry_func, grouped by source file.

    Extracts a throwaway copy of proj_dir with the very machinery the main
    pipeline uses — ``run_extraction`` plus ``_build_call_graph`` from
    generate_topdown_layers, both codegraph-backed whenever a codegraph index
    can be built — then builds the call graph rooted at ``entry_func``
    (optionally restricted to chains reaching ``end_funcs``) and returns two
    source-file-keyed groupings:

        (all_by_source, keep_by_source)

    ``all_by_source`` covers every extractable function; ``keep_by_source``
    covers only the selected ones. proj_dir is read but never modified:
    extraction, the codegraph index and all scratch state live under a sibling
    selection copy that is discarded before returning.
    """
    # A full source copy lets codegraph index the project (writing .codegraph/)
    # and lets run_extraction/_build_call_graph run exactly as they do in
    # run_pipeline — without ever touching proj_dir. _build_call_graph resolves
    # the codegraph index via the copy's parent (see CodeGraphExtractor
    # .from_proj_dir), matching how run_pipeline drives it against work_dir.
    sel_dir = proj_dir + ".fm-entry-select"
    work_dir = os.path.join(sel_dir, "fm_agent")
    _make_run_copy(proj_dir, sel_dir)
    try:
        source_files = _enumerate_source_files(sel_dir)
        if not source_files:
            raise ValueError(f"no extractable source files found under {proj_dir!r}")

        # One all-encompassing phase, so _build_call_graph's within-phase edges
        # span the entire project (every reachable callee is retained).
        phase = {"phase": 0, "name": "all",
                 "modules": [{"name": "all", "source_files": source_files}]}
        # _make_run_copy brings along any existing fm_agent/; start the selection
        # extraction from a clean slate so no stale extracted_functions leak in.
        shutil.rmtree(work_dir, ignore_errors=True)
        os.makedirs(work_dir, exist_ok=True)
        with open(os.path.join(work_dir, "phases.json"), "w") as f:
            json.dump({"phases": [phase]}, f)

        try_codegraph_init(sel_dir)
        run_extraction(sel_dir, work_dir=work_dir, force=True)

        phase_files = _collect_phase_files(work_dir, phase)
        if not phase_files:
            raise ValueError(f"no extractable functions found under {proj_dir!r}")
        (
            callees_map,
            _callers,
            _all_callees,
            _file_map,
            _module_map,
            _edge_aliases,
        ) = _build_call_graph(
            phase_files,
            work_dir,
            extra_call_edges=extra_call_edges,
        )
        all_fqns = {_file_to_fqn(fp, work_dir) for fp, _mod in phase_files}

        if entry_func not in all_fqns:
            raise ValueError(
                f"entry_func {entry_func!r} not found among extracted functions under proj_dir"
            )

        # BFS the call graph reachable from the entry point.
        call_graph = {}
        queue = deque([entry_func])
        while queue:
            fqn = queue.popleft()
            if fqn in call_graph:
                continue
            callees = callees_map.get(fqn, set())
            call_graph[fqn] = sorted(callees)
            for callee in callees:
                if callee not in call_graph:
                    queue.append(callee)

        # Every extractable function, grouped by source file.
        all_by_source = defaultdict(set)
        for fqn in all_fqns:
            all_by_source[_entry_func_source_rel(fqn)].add(_fqn_to_ident(fqn))
    finally:
        shutil.rmtree(sel_dir, ignore_errors=True)

    # Keep only functions on a call chain from entry_func to one of end_funcs.
    if end_funcs:
        unreachable = sorted(set(end_funcs) - set(call_graph))
        call_graph = _restrict_to_chains(call_graph, entry_func, end_funcs)
        if unreachable:
            logging.warning(
                "[EntryPipeline] %d end function(s) are not reachable from %s: %s",
                len(unreachable), entry_func, ", ".join(unreachable[:5]),
            )
        if not call_graph:
            raise ValueError(
                f"none of the requested end_funcs are reachable from entry_func {entry_func!r}"
            )

    print(
        f"[EntryPipeline] Selected {len(call_graph)} of {len(all_fqns)} function(s) "
        f"from entry {entry_func}."
    )

    # Map the selected FQNs back to their (source file, function identifier).
    keep_by_source = defaultdict(set)
    for fqn in call_graph:
        keep_by_source[_entry_func_source_rel(fqn)].add(_fqn_to_ident(fqn))

    return all_by_source, keep_by_source
