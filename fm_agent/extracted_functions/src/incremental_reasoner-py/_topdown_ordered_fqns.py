# [SPEC]
# Unit: src/incremental_reasoner.py
#
# _topdown_ordered_fqns(work_dir, extra_call_edges=None) -> list
#
# Pre-condition:
#   - work_dir is the path to an fm_agent workspace directory that contains
#     spec_prompts/ as a subdirectory and a valid phases.json at work_dir/phases.json.
#   - extra_call_edges, when provided, is passed through to generate_topdown_layers
#     and must conform to the format that function expects.
#
# Post-condition:
#   - Returns a list of fully-qualified function names (FQNs), ordered such that
#     callers precede the callees they depend on (top-down order).
#   - The ordering follows: ascending phase number, then ascending layer number within
#     each phase, then the order of functions as listed within each layer (the order
#     produced by the full run's generate_topdown_layers).
#   - Every FQN present in the per-phase topdown-layer JSON files appears exactly once
#     in the returned list.
#   - As a side effect, the per-phase topdown-layer JSON files under
#     work_dir/spec_prompts/ (phase_NN_topdown_layers.json) are regenerated via
#     generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges), mirroring
#     the full run's layer generation.
# [SPEC]

# [INFO]
# generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges) -> None
#   Pre-condition: work_dir contains a valid phases.json and extracted_functions/ with
#     complete extracted function files for all phases.
#   Post-condition: Writes phase_NN_topdown_layers.json files under
#     work_dir/spec_prompts/ for each phase; each file contains a topological ordering
#     of functions where callees are assigned to lower-numbered layers than their callers.
# [SPLIT]
# _load_phases(work_dir) -> dict
#   Pre-condition: work_dir/phases.json exists and is valid JSON conforming to the
#     phases schema ({project, languages, phases: [{phase, name, ...}]}).
#   Post-condition: Returns the parsed phases.json data structure.
# [SPLIT]
# json.load(open(layers_path, "r")) -> dict
#   Pre-condition: layers_path points to a valid phase_NN_topdown_layers.json file
#     containing a "layers" key with a list of layer objects, each with "layer" and
#     "functions" keys.
#   Post-condition: Returns the parsed layer data structure.
# [INFO]

def _topdown_ordered_fqns(work_dir, extra_call_edges=None):
    """
    Return every extracted-function FQN in the top-down order used by run_pipeline for
    spec generation: phases in ascending phase number, layers from 0 upward, and the
    functions in the order listed within each layer (callers precede the callees they
    depend on).

    Regenerates the per-phase topdown-layer JSON files under work_dir/spec_prompts/ as
    a side effect (mirroring run_pipeline's generate_topdown_layers(work_dir) call).
    """
    generate_topdown_layers(work_dir, extra_call_edges=extra_call_edges)
    phases_data = _load_phases(work_dir)
    spec_prompts_dir = os.path.join(work_dir, "spec_prompts")

    ordered = []
    for phase_info in sorted(phases_data.get("phases", []), key=lambda p: p["phase"]):
        phase_num = phase_info["phase"]
        layers_path = os.path.join(
            spec_prompts_dir, f"phase_{phase_num:02d}_topdown_layers.json"
        )
        if not os.path.exists(layers_path):
            continue
        with open(layers_path, "r") as f:
            layers_data = json.load(f)
        for layer in sorted(layers_data.get("layers", []), key=lambda l: l["layer"]):
            for func in layer.get("functions", []):
                ordered.append(func["name"])
    return ordered
