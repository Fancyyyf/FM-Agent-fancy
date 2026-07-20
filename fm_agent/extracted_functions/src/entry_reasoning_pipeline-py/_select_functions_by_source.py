# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_select_functions_by_source.py
#
# _select_functions_by_source(proj_dir, entry_func, end_funcs, extra_call_edges=None) -> (dict[str, set[str]], dict[str, set[str]])
#
# Pre-condition:
#   - proj_dir is an existing directory (the project root)
#   - entry_func is a non-empty fully-qualified function name string
#   - end_funcs is an iterable of zero or more fully-qualified function name strings
#   - extra_call_edges, when provided, contributes supplemental call edges through a
#     format recognized by _build_call_graph
#
# Post-condition:
#   - proj_dir is never mutated; all mutations occur in a temporary sibling directory
#     that is destroyed before this function returns
#   - Returns a tuple (all_by_source, keep_by_source) where:
#     - all_by_source is a dict mapping each source-file relative path to the set of
#       ALL function names that were extractable from that source file
#     - keep_by_source is a dict mapping each source-file relative path to the set of
#       function names that are transitively reachable from entry_func in the static
#       call graph; when end_funcs is non-empty, this set is further restricted to
#       function names that lie on at least one call-chain path from entry_func to
#       some member of end_funcs
#   - Raises ValueError when:
#     - No extractable source files are found under proj_dir
#     - No extractable functions are found under proj_dir
#     - entry_func is not among the extracted functions
#     - end_funcs is non-empty and no member of end_funcs is reachable from entry_func
#       in the call graph
#   - When extra_call_edges is provided, its supplemental edges contribute to the call
#     graph used for reachability analysis
# [SPEC]

# [INFO]
# _make_run_copy(src, dst) -> None
#   Pre-condition: src is an existing directory
#   Post-condition: dst is a copy of src at the time of the call; src is not modified
# [SPLIT]
# _enumerate_source_files(proj_dir) -> list[str]
#   Pre-condition: proj_dir is an existing directory
#   Post-condition: Returns a list of source-file relative paths for all extractable
#     source files under proj_dir
# [SPLIT]
# try_codegraph_init(proj_dir) -> None
#   Pre-condition: proj_dir is an existing directory
#   Post-condition: If a codegraph index can be built for proj_dir, it is initialized;
#     otherwise, no error is raised and codegraph-accelerated extraction silently degrades
# [SPLIT]
# run_extraction(proj_dir, work_dir, force) -> None
#   Pre-condition: proj_dir is a project directory; work_dir exists
#   Post-condition: Extracted function files are written under work_dir/extracted_functions/;
#     does not modify proj_dir
# [SPLIT]
# _collect_phase_files(work_dir, phase) -> list
#   Post-condition: Returns a list of (extracted_file_relative_path, module_name) tuples
#     for the given phase, read from the extracted functions tree under work_dir
# [SPLIT]
# _build_call_graph(phase_files, work_dir, extra_call_edges) -> (dict, dict, dict, dict, dict, dict)
#   Pre-condition: phase_files is populated with extracted function paths
#   Post-condition: Returns a tuple containing at least a callees_map (mapping each FQN
#     to its set of callee FQNs) and related call-graph structures; extra_call_edges, when
#     provided, contributes supplemental edges
# [SPLIT]
# _file_to_fqn(fp, work_dir) -> str
#   Post-condition: Returns the fully-qualified function name derived from the extracted
#     function file path fp
# [SPLIT]
# _entry_func_source_rel(fqn) -> str
#   Post-condition: Returns the source-file relative path corresponding to the given FQN
# [SPLIT]
# _restrict_to_chains(call_graph, entry_func, end_funcs) -> dict
#   Pre-condition: call_graph is a mapping from FQN to list of callee FQNs; end_funcs is
#     a non-empty collection of FQN strings; entry_func is reachable to at least one end_func
#   Post-condition: Returns a dict containing only those FQNs that lie on at least one
#     call-chain path from entry_func to a member of end_funcs
# [INFO]

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
            all_by_source[_entry_func_source_rel(fqn)].add(fqn.split("::")[-1])
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

    # Map the selected FQNs back to their (source file, function name).
    keep_by_source = defaultdict(set)
    for fqn in call_graph:
        keep_by_source[_entry_func_source_rel(fqn)].add(fqn.split("::")[-1])

    return all_by_source, keep_by_source
