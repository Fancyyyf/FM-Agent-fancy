def _compute_layers(phase_fqns, callees_map, callers_map):
    """Compute topological layers using Kahn's algorithm with cycle handling.

    Returns list of layer dicts: [{"layer": N, "functions": [...], "cycle_resolution": bool}, ...]
    """
    phase_set = set(phase_fqns)

    # Build in-phase caller counts
    remaining = set(phase_set)
    assigned = {}  # fqn -> layer index
    layers = []

    while remaining:
        # Find functions whose all same-phase callers are already assigned
        ready = set()
        for fqn in remaining:
            phase_callers = callers_map.get(fqn, set()) & phase_set
            unassigned_callers = phase_callers - set(assigned.keys())
            if not unassigned_callers:
                ready.add(fqn)

        if ready:
            layer_idx = len(layers)
            for fqn in ready:
                assigned[fqn] = layer_idx
            layers.append({"layer": layer_idx, "functions": sorted(ready), "cycle_resolution": False})
            remaining -= ready
        else:
            # Cycle detected — use Tarjan's SCC
            # Build subgraph of remaining functions
            sub_edges = {}
            for fqn in remaining:
                sub_edges[fqn] = callees_map.get(fqn, set()) & remaining

            # Compute SCCs on the *caller* graph (edges from callee to caller)
            # Actually we need topological ordering of SCCs by the caller relationship.
            # An SCC can be assigned once all SCCs that *call into it* are assigned.
            # So we use the callers graph direction for the SCC ordering.
            caller_edges_sub = {}
            for fqn in remaining:
                caller_edges_sub[fqn] = callers_map.get(fqn, set()) & remaining

            sccs = _tarjan_scc(remaining, caller_edges_sub)

            # Build SCC DAG and assign layers
            fqn_to_scc = {}
            for i, scc in enumerate(sccs):
                for fqn in scc:
                    fqn_to_scc[fqn] = i

            # Build DAG between SCCs based on caller edges
            scc_callers = defaultdict(set)  # scc_idx -> set of scc_idx that call into it
            for fqn in remaining:
                scc_i = fqn_to_scc[fqn]
                for caller_fqn in callers_map.get(fqn, set()) & remaining:
                    scc_j = fqn_to_scc[caller_fqn]
                    if scc_i != scc_j:
                        scc_callers[scc_i].add(scc_j)

            # Topological sort of SCCs
            scc_assigned = {}
            scc_remaining = set(range(len(sccs)))

            while scc_remaining:
                scc_ready = set()
                for scc_idx in scc_remaining:
                    unassigned_scc_callers = scc_callers.get(scc_idx, set()) - set(scc_assigned.keys())
                    if not unassigned_scc_callers:
                        scc_ready.add(scc_idx)

                if not scc_ready:
                    # Should not happen if Tarjan is correct, but handle gracefully
                    # Assign all remaining to the same layer
                    layer_idx = len(layers)
                    all_fqns = set()
                    for scc_idx in scc_remaining:
                        all_fqns.update(sccs[scc_idx])
                    for fqn in all_fqns:
                        assigned[fqn] = layer_idx
                    layers.append({"layer": layer_idx, "functions": sorted(all_fqns), "cycle_resolution": True})
                    remaining -= all_fqns
                    break

                layer_idx = len(layers)
                layer_fqns = set()
                is_cycle = False
                for scc_idx in scc_ready:
                    scc_assigned[scc_idx] = layer_idx
                    layer_fqns.update(sccs[scc_idx])
                    if len(sccs[scc_idx]) > 1:
                        is_cycle = True

                for fqn in layer_fqns:
                    assigned[fqn] = layer_idx
                layers.append({"layer": layer_idx, "functions": sorted(layer_fqns), "cycle_resolution": is_cycle})
                remaining -= layer_fqns
                scc_remaining -= scc_ready

    return layers
