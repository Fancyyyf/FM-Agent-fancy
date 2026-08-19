def _build_call_graph(phase_files, proj_dir, global_stem_to_fqns=None, extra_call_edges=None):
    """Build callees_map and callers_map for a set of phase files.

    Args:
        phase_files: list of (filepath, module_name) tuples
        proj_dir: project root directory
        global_stem_to_fqns: optional global stem->set(fqn) mapping across all phases,
                             used to compute all_callees (cross-phase)
        extra_call_edges: optional iterable of supplemental CallEdge objects.
                          caller.fqn is exact; caller.callsite_names are matched
                          only against explicitly listed source callsite names.

    Returns:
        (callees_map, callers_map, all_callees_map, file_map, module_map,
        edge_aliases_map) where keys are FQNs.
        callees_map/callers_map contain only within-phase edges.
        all_callees_map contains callees from any phase.
        edge_aliases_map maps callee -> caller -> supplemental callee labels
        that may appear as callee names in a caller's .info.json sidecar.
    """
    # Build FQN mappings
    fqn_map = {}  # filepath -> fqn
    stem_to_fqns = defaultdict(set)  # stem -> set of fqns (phase-local)
    file_map = {}  # fqn -> filepath
    module_map = {}  # fqn -> module_name

    for filepath, module_name in phase_files:
        fqn = _file_to_fqn(filepath, proj_dir)
        fqn_map[filepath] = fqn
        file_map[fqn] = filepath
        module_map[fqn] = module_name
        stem = fqn.split("::")[-1]
        stem_to_fqns[stem].add(fqn)

    phase_fqns = set(fqn_map.values())
    # For call-site detection, use global stems if available
    effective_stem_to_fqns = global_stem_to_fqns if global_stem_to_fqns else stem_to_fqns
    # All extracted FQNs (across phases when a global map is supplied), used to
    # keep only codegraph callees that correspond to an extracted function.
    known_fqns = {
        fqn
        for fqns in effective_stem_to_fqns.values()
        for fqn in fqns
    }
    extra_edges_by_caller_fqn, extra_edges_by_callsite = _resolve_extra_call_edges(
        extra_call_edges,
        phase_fqns=phase_fqns,
        known_fqns=known_fqns,
    )
    known_stems = set(effective_stem_to_fqns.keys()) | set(extra_edges_by_callsite.keys())

    callees_map = defaultdict(set)  # fqn -> set of callee fqns (within phase)
    callers_map = defaultdict(set)  # fqn -> set of caller fqns (within phase)
    all_callees_map = defaultdict(set)  # fqn -> set of callee fqns (any phase)
    edge_aliases_map = defaultdict(lambda: defaultdict(set))  # callee -> caller -> aliases

    phase_langs = {_detect_lang_from_ext(fp) for fp, _ in phase_files if _detect_lang_from_ext(fp)}
    registry_edges, registry_langs = call_edges_all(proj_dir, phase_langs)

    for filepath, module_name in phase_files:
        fqn = fqn_map[filepath]
        lang_key = _detect_lang_from_ext(filepath)
        if not lang_key:
            continue

        called_stems = set()
        if lang_key in registry_langs:
            # codegraph: edges are already precise caller_fqn -> callee_fqn (the
            # exact node codegraph resolved). Keep only callees that are extracted
            # functions; drop external/library targets.
            callee_fqns = {c for c in registry_edges.get(fqn, set())
                           if c != fqn and c in known_fqns}
            if extra_edges_by_callsite:
                keywords = _get_keywords_for_lang(lang_key)
                try:
                    with open(filepath, "r", errors="replace") as f:
                        text = f.read()
                except OSError:
                    text = ""
                called_stems = _find_call_sites(
                    text, lang_key, set(extra_edges_by_callsite.keys()), keywords
                )
        else:
            # regex fallback: detect bare-name call sites, then resolve each stem
            # to every same-named FQN (an over-approximation — unchanged).
            keywords = _get_keywords_for_lang(lang_key)
            try:
                with open(filepath, "r", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            called_stems = _find_call_sites(text, lang_key, known_stems, keywords)
            callee_fqns = {cf for stem in called_stems
                           for cf in effective_stem_to_fqns.get(stem, set()) if cf != fqn}

        for callee_fqn in callee_fqns:
            all_callees_map[fqn].add(callee_fqn)
            if callee_fqn in phase_fqns:
                callees_map[fqn].add(callee_fqn)
                callers_map[callee_fqn].add(fqn)

        for stem in called_stems:
            for edge in extra_edges_by_callsite.get(stem, ()):
                _add_resolved_extra_edge(
                    fqn,
                    edge,
                    phase_fqns,
                    callees_map,
                    callers_map,
                    all_callees_map,
                    edge_aliases_map,
                )

        for edge in extra_edges_by_caller_fqn.get(fqn, ()):
            _add_resolved_extra_edge(
                fqn,
                edge,
                phase_fqns,
                callees_map,
                callers_map,
                all_callees_map,
                edge_aliases_map,
            )

    return callees_map, callers_map, all_callees_map, file_map, module_map, edge_aliases_map
