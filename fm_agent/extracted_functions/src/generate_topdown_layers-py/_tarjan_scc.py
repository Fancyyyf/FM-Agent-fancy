# [SPEC]
# Unit: src/generate_topdown_layers-py/_tarjan_scc.py
#
# _tarjan_scc(nodes, edges) -> list[set]
#
# Pre-condition:
#   - nodes is an iterable of hashable, equality-comparable node identifiers
#   - edges is a mapping from each node to an iterable of successor nodes
#     (outgoing directed edges); successor nodes that are not members of the
#     iterable nodes are permitted — they are visited but do not contribute SCCs
#     to the result beyond their role as intermediate targets
#
# Post-condition:
#   - Returns a list of sets, each set representing one strongly connected
#     component (SCC); the list is ordered in reverse topological order: for any
#     directed edge from a node in SCC at position i to a node in SCC at position
#     j, i ≤ j (no edge goes from a later SCC in the list to an earlier SCC)
#   - Every node in nodes appears in exactly one SCC in the result
#   - Each returned SCC is a maximal strongly connected subgraph restricted to
#     nodes: for every ordered pair of distinct nodes (u, v) in the same SCC,
#     there exists a directed path u → ... → v using only nodes from nodes as
#     intermediate vertices, and no proper superset containing that SCC satisfies
#     this property while also being a subset of nodes
#   - A node that cannot reach any other node in nodes that can also reach it
#     back appears as a singleton SCC (a set containing exactly that node)
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _tarjan_scc(nodes, edges):
    """Compute strongly connected components using Tarjan's algorithm (iterative).

    Args:
        nodes: iterable of node identifiers
        edges: dict mapping node -> set of successor nodes

    Returns:
        list of SCCs (each SCC is a set of nodes), in reverse topological order
    """
    index_counter = 0
    scc_stack = []
    on_stack = set()
    index_map = {}
    lowlink = {}
    result = []

    for node in nodes:
        if node in index_map:
            continue
        # Iterative DFS using an explicit call stack.
        # Each frame is (v, iterator_over_successors, is_initial_visit)
        call_stack = [(node, iter(edges.get(node, set())), True)]
        while call_stack:
            v, successors, initial = call_stack[-1]
            if initial:
                index_map[v] = index_counter
                lowlink[v] = index_counter
                index_counter += 1
                scc_stack.append(v)
                on_stack.add(v)
                # Mark as visited so we don't re-init
                call_stack[-1] = (v, successors, False)

            advanced = False
            for w in successors:
                if w not in index_map:
                    call_stack.append((w, iter(edges.get(w, set())), True))
                    advanced = True
                    break
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index_map[w])

            if advanced:
                continue

            # All successors processed — check if v is a root
            if lowlink[v] == index_map[v]:
                scc = set()
                while True:
                    w = scc_stack.pop()
                    on_stack.discard(w)
                    scc.add(w)
                    if w == v:
                        break
                result.append(scc)

            call_stack.pop()
            if call_stack:
                parent = call_stack[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[v])

    return result
