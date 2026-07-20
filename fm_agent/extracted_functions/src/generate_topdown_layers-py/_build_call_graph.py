# [SPEC]
# Unit: src/generate_topdown_layers-py/_build_call_graph.py
#
# _build_call_graph(phase_files, proj_dir, global_stem_to_fqns=None, extra_call_edges=None)
#   -> tuple[dict, dict, dict, dict, dict, dict]
#
# Pre-condition:
#   - phase_files is a non-empty list of (filepath, module_name) tuples, where
#     filepath is a path to an extracted function source file that exists and is
#     readable, and module_name is a string from phases.json
#   - proj_dir is the project root directory path
#   - global_stem_to_fqns, if not None, is a dict mapping function-name stems
#     to sets of FQN strings across all phases
#   - extra_call_edges, if not None, is an iterable of CallEdge objects each
#     specifying a caller (by exact FQN and/or callsite names) and a callee
#     (by exact FQN with optional info_names)
#
# Post-condition:
#   - Returns a 6-tuple of dicts: (callees_map, callers_map, all_callees_map,
#     file_map, module_map, edge_aliases_map), all keyed by FQN strings
#   - callees_map[fqn]: set of FQNs called by fqn within the same phase; every
#     callee FQN corresponds to an extracted function and is never equal to fqn
#   - callers_map[fqn]: set of FQNs from the same phase that call fqn; every
#     caller FQN is a member of the phase's FQN set
#   - all_callees_map[fqn]: set of FQNs called by fqn across all phases — a
#     superset of callees_map[fqn]; when global_stem_to_fqns is None, this set
#     contains only within-phase callees; when provided, it may include FQNs
#     from other phases
#   - file_map[fqn]: absolute path to the extracted function file for fqn
#   - module_map[fqn]: module name string from phases.json for fqn
#   - edge_aliases_map[callee_fqn][caller_fqn]: set of supplemental info names
#     for the edge from caller_fqn to callee_fqn, derived from extra_call_edges
#     and static analysis; absent entry implies the empty set
#   - Callee resolution uses the codegraph backend when available for the file's
#     language; otherwise falls back to regex-based bare-name call-site detection
#     where each detected stem resolves to every FQN mapping to that stem (an
#     over-approximation that only includes extracted-function targets)
#   - Extra call edges from extra_call_edges are merged into the returned maps
#     for callers matched by exact FQN or by callsite name detected in source
#   - If a source file cannot be opened for reading, no callee edges are added
#     for that file and it is silently skipped
# [SPEC]

# [INFO]
# _file_to_fqn(filepath: str, proj_dir: str) -> str
#   Pre-condition: filepath is a path to an extracted function file under proj_dir
#   Post-condition: returns the FQN derived from filepath by stripping the
#     extension and joining directory components with "::"
# [SPLIT]
# _resolve_extra_call_edges(extra_call_edges, phase_fqns, known_fqns) -> tuple[dict, dict]
#   Pre-condition: extra_call_edges is None or an iterable of CallEdge objects;
#     phase_fqns is a set of FQNs within the current phase; known_fqns is a set
#     of all known FQNs across all phases
#   Post-condition: returns (edges_by_caller_fqn, edges_by_callsite) where both
#     are dicts; edges_by_caller_fqn maps exact caller FQNs to lists of edges,
#     and edges_by_callsite maps callsite name strings to lists of edges; only
#     edges whose callee FQN is in known_fqns are retained
# [SPLIT]
# _detect_lang_from_ext(filepath: str) -> str | None
#   Pre-condition: filepath is a string ending with a file extension
#   Post-condition: returns the language key string corresponding to the file
#     extension, or None if the extension is not recognized
# [SPLIT]
# call_edges_all(proj_dir: str, phase_langs: set[str]) -> tuple[dict, set[str]]
#   Pre-condition: proj_dir is the project root; phase_langs is a set of
#     language key strings
#   Post-condition: returns (registry_edges, registry_langs) where
#     registry_edges maps caller FQNs to sets of callee FQNs resolved by
#     codegraph, and registry_langs is the subset of phase_langs for which
#     codegraph resolution is available
# [SPLIT]
# _get_keywords_for_lang(lang_key: str) -> set[str]
#   Pre-condition: lang_key is a recognized language key string
#   Post-condition: returns the set of language-reserved keywords to exclude
#     from call-site detection for the given language
# [SPLIT]
# _find_call_sites(text: str, lang_key: str, stems_to_find: set[str], keywords: set[str]) -> set[str]
#   Pre-condition: text is source code text; lang_key is a recognized language
#     key; stems_to_find is a set of function-name stems; keywords is a set of
#     reserved keywords to exclude
#   Post-condition: returns the subset of stems_to_find that appear as bare-name
#     call sites in text (not preceded by a definition keyword or within a
#     string/comment context for the given language)
# [SPLIT]
# _add_resolved_extra_edge(caller_fqn, edge, phase_fqns, callees_map, callers_map,
#   all_callees_map, edge_aliases_map)
#   Pre-condition: caller_fqn is a string; edge is a CallEdge object with
#     callee.fqn; the remaining arguments are mutable dicts keyed by FQN
#   Post-condition: adds edge.callee.fqn to all_callees_map[caller_fqn]; if
#     edge.callee.fqn is in phase_fqns, also adds it to callees_map and
#     callers_map; if edge.callee.info_names is non-empty, adds them to
#     edge_aliases_map[edge.callee.fqn][caller_fqn]
# [INFO]

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
        that may appear in a caller's [INFO] block.
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
