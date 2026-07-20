# [SPEC]
# Unit: src/generate_topdown_layers-py/generate_topdown_layers.py
#
# generate_topdown_layers(proj_dir, phase_numbers=None, extra_call_edges=None)
#
# Pre-condition:
#   - proj_dir is a valid directory containing fm_agent/phases.json with at minimum the key "phases" (a list of phase objects) and optionally other phase metadata
#   - Each phase in phases.json must have integer "phase" and string "name" keys
#   - Extracted function files exist under fm_agent/extracted_functions/ for at least one phase; each filename encodes a function name
#   - If phase_numbers is provided, every element is a valid phase number present in phases.json
#   - If extra_call_edges is provided, each edge identifies a caller (by FQN and/or callsite names) and a callee (by FQN)
#
# Post-condition:
#   - For every phase in phases.json whose phase number matches the phase_numbers filter (or for all phases if phase_numbers is None), writes one file fm_agent/spec_prompts/phase_NN_topdown_layers.json where NN is the zero-padded phase number
#   - Each output JSON contains the phase number, phase name, total number of functions within the phase (total_functions), total number of topological layers (total_layers), and a "layers" list of layer objects sorted by ascending layer index
#   - Each layer object has a "layer" key (0-indexed integer); if the layer resolves a strongly connected component (mutual recursion), it also contains "cycle_resolution": true
#   - Within each layer, "functions" is a list of entries, each with: "name" (FQN), "file" (relative path from proj_dir to the extracted function), "unit" (module name), phaseN_callers (FQNs of in-phase callers), phaseN_callees (FQNs of in-phase callees), and all_callees (FQNs of callees across all phases, including cross-phase edges)
#   - Callers appear in strictly higher-numbered layers than their callees, except when both belong to the same SCC (cycle-resolution layer)
#   - If edge_aliases_map contains supplemental names for a callee's entry from a particular caller, the function entry includes a phaseN_callee_info_names_by_caller map of caller FQN to sorted list of info names
#   - If extra_call_edges is provided, the resulting call graph includes those edges in addition to edges derived from static analysis
#   - Returns a list of absolute paths to the written JSON files, in the order the phases appear in phases.json; a phase with no extracted functions is skipped with a log warning and does not appear in the output
# [SPEC]

# [INFO]
# _load_phases(proj_dir: str) -> dict
#   Pre-condition: proj_dir/fm_agent/phases.json exists and is valid JSON
#   Post-condition: returns the parsed JSON object containing at minimum a "phases" list; each phase entry has integer "phase" and string "name" keys
# [SPLIT]
# _collect_phase_files(proj_dir: str, phase_info: dict) -> list[tuple[str, object]]
#   Pre-condition: phase_info has module and source_file information; extracted function files exist under proj_dir/fm_agent/extracted_functions/
#   Post-condition: returns a list of (filepath, metadata) pairs where each filepath is a path to a single-function extracted file belonging to this phase; the list is empty if no extracted files exist for this phase
# [SPLIT]
# _file_to_fqn(filepath: str, proj_dir: str) -> str
#   Pre-condition: filepath is a path to an extracted function file under proj_dir/fm_agent/extracted_functions/
#   Post-condition: returns the fully-qualified name derived by stripping the extension from filepath and joining directory components of the path below extracted_functions/ with "::" separators; the filename component becomes the last segment
# [SPLIT]
# _build_call_graph(phase_files: list, proj_dir: str, global_stem_to_fqns: dict, extra_call_edges=None) -> tuple[dict, dict, dict, dict, dict, dict]
#   Pre-condition: phase_files is a non-empty list of (filepath, metadata) pairs; global_stem_to_fqns maps function-name stems to sets of FQNs across all phases
#   Post-condition: returns a 6-tuple of (callees_map, callers_map, all_callees_map, file_map, module_map, edge_aliases_map), all keyed by FQN; callees_map[fqn] is the set of FQNs called by fqn, callers_map[fqn] is the set of FQNs that call fqn, all_callees_map[fqn] includes callees from all phases, file_map[fqn] is the absolute file path, module_map[fqn] is the module name, and edge_aliases_map[callee_fqn][caller_fqn] is a set of supplemental info names from extra_call_edges or static analysis
# [SPLIT]
# _compute_layers(phase_fqns: set[str], callees_map: dict, callers_map: dict) -> list[dict]
#   Pre-condition: phase_fqns is the set of all FQNs in this phase; callees_map and callers_map cover all FQNs in phase_fqns with zero or more edges each
#   Post-condition: returns a list of layer dicts sorted by ascending layer index; each dict has "layer" (0-indexed integer), "functions" (list of FQNs in this layer), and optionally "cycle_resolution": true when the layer contains an SCC; every FQN in phase_fqns appears in exactly one layer; for every caller-callee pair where both are in phase_fqns, the callee's layer index is ≤ the caller's layer index, with equality only when they belong to the same cycle-resolution layer
# [INFO]

def generate_topdown_layers(proj_dir, phase_numbers=None, extra_call_edges=None):
    """Generate topdown layer JSON files for the specified phases (or all phases).

    Args:
        proj_dir: project root directory
        phase_numbers: list of phase numbers to process, or None for all
        extra_call_edges: optional iterable of supplemental caller/callee edges

    Returns:
        list of output file paths written
    """
    phases_data = _load_phases(proj_dir)

    output_dir = os.path.join(proj_dir, "spec_prompts")
    os.makedirs(output_dir, exist_ok=True)

    # Build global stem->FQN mapping across ALL phases for all_callees
    global_stem_to_fqns = defaultdict(set)
    for pi in phases_data["phases"]:
        for filepath, _ in _collect_phase_files(proj_dir, pi):
            fqn = _file_to_fqn(filepath, proj_dir)
            stem = fqn.split("::")[-1]
            global_stem_to_fqns[stem].add(fqn)

    output_files = []

    for phase_info in phases_data["phases"]:
        phase_num = phase_info["phase"]
        phase_name = phase_info["name"]

        if phase_numbers and phase_num not in phase_numbers:
            continue

        # 1.2 Collect files
        phase_files = _collect_phase_files(proj_dir, phase_info)
        if not phase_files:
            logging.warning(f"Phase {phase_num} ({phase_name}): no extracted files found, skipping.")
            continue

        # 1.4 Build call graph (also returns file_map and module_map)
        (
            callees_map,
            callers_map,
            all_callees_map,
            file_map,
            module_map,
            edge_aliases_map,
        ) = _build_call_graph(
            phase_files, proj_dir, global_stem_to_fqns, extra_call_edges=extra_call_edges
        )
        phase_fqns = set(file_map.keys())

        # 1.5 Compute topological layers
        layers = _compute_layers(phase_fqns, callees_map, callers_map)

        # Build phase-specific key names
        phase_callers_key = f"phase{phase_num}_callers"
        phase_callees_key = f"phase{phase_num}_callees"
        phase_info_names_key = f"phase{phase_num}_callee_info_names_by_caller"

        # 1.6 Build output JSON
        total_functions = len(phase_fqns)
        total_layers = len(layers)

        output_layers = []
        for layer_info in layers:
            layer_dict = {
                "layer": layer_info["layer"],
            }
            if layer_info["cycle_resolution"]:
                layer_dict["cycle_resolution"] = True

            func_entries = []
            for fqn in layer_info["functions"]:
                filepath = file_map[fqn]
                rel_path = os.path.relpath(filepath, proj_dir)
                unit = module_map.get(fqn, "")

                phase_callers = sorted(callers_map.get(fqn, set()) & phase_fqns)
                phase_callees = sorted(callees_map.get(fqn, set()) & phase_fqns)
                all_callees = sorted(all_callees_map.get(fqn, set()))

                entry = {
                    "name": fqn,
                    "file": rel_path,
                    "unit": unit,
                    phase_callers_key: phase_callers,
                    phase_callees_key: phase_callees,
                    "all_callees": all_callees,
                }
                info_names_by_caller = {
                    caller: sorted(info_names)
                    for caller, info_names in edge_aliases_map.get(fqn, {}).items()
                    if caller in phase_fqns and info_names
                }
                if info_names_by_caller:
                    entry[phase_info_names_key] = info_names_by_caller
                func_entries.append(entry)

            layer_dict["functions"] = func_entries
            output_layers.append(layer_dict)

        output = {
            "phase": phase_num,
            "phase_name": phase_name,
            "total_functions": total_functions,
            "total_layers": total_layers,
            "layers": output_layers,
        }

        # Write output
        out_path = os.path.join(output_dir, f"phase_{phase_num:02d}_topdown_layers.json")
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        output_files.append(out_path)
        print(f"[TopdownLayers] Phase {phase_num} ({phase_name}): {total_functions} functions, {total_layers} layers -> {os.path.relpath(out_path, proj_dir)}")

    return output_files
