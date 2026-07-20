# [SPEC]
# Unit: src/generate_topdown_layers-py/_compute_layers.py
#
# _compute_layers(phase_fqns, callees_map, callers_map) -> list[dict]
#
# Pre-condition:
#   - phase_fqns is a non-empty iterable of unique, hashable function identifiers (FQNs)
#   - callees_map maps each FQN to an iterable of FQNs it calls (may be empty); referenced callee FQNs that belong to this phase must be members of phase_fqns
#   - callers_map maps each FQN to an iterable of FQNs that call it (may be empty); referenced caller FQNs that belong to this phase must be members of phase_fqns
#
# Post-condition:
#   - Returns a list of layer dicts, sorted by ascending "layer" (0-indexed integer)
#   - Each layer dict contains: "layer" (int), "functions" (list of FQNs in lexicographic order), and "cycle_resolution" (bool)
#   - Every FQN in phase_fqns appears in exactly one layer's "functions" list
#   - For every directed edge (caller → callee) where both endpoints are in phase_fqns: the callee's layer index is less than or equal to the caller's layer index
#   - Equality (callee and caller in the same layer) occurs only when the two functions belong to the same strongly connected component (mutual recursion), and the layer is marked with "cycle_resolution": true
#   - "cycle_resolution" is true when the layer contains at least one SCC with two or more members; it is false when all SCCs in the layer are singletons (no mutual recursion resolved)
#   - When no cycles exist, layers are assigned by applying Kahn's algorithm on the caller graph: a function enters the current layer when all its in-phase callers have already been assigned to strictly earlier layers
# [SPEC]

# [INFO]
# _tarjan_scc(nodes, edges) -> list[list]
#   Pre-condition: nodes is an iterable of hashable node identifiers; edges maps each node to an iterable of its outgoing neighbors (other node identifiers)
#   Post-condition: returns a list of SCCs in reverse topological order (no edge from a later SCC to an earlier SCC); each SCC is a maximal set of nodes where every node is reachable from every other node via directed paths restricted to nodes; every node in nodes appears in exactly one SCC
# [INFO]

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
