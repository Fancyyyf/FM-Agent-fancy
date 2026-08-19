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
