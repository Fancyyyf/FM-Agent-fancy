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
