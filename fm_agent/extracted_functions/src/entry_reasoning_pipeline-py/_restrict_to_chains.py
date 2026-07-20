# [SPEC]
# Unit: fm_agent/extracted_functions/src/entry_reasoning_pipeline-py/_restrict_to_chains.py
#
# _restrict_to_chains(call_graph, entry_func, end_funcs) -> dict
#
# Pre-condition:
#   - call_graph is a dict mapping each FQN string to a list of callee FQN strings, where every callee referenced in any value list is also a key in call_graph (the graph is closed under its FQN space)
#   - entry_func is an FQN string that is a key in call_graph
#   - end_funcs is an iterable of FQN strings, possibly empty
#
# Post-condition:
#   - call_graph is never mutated; a new dict is returned (or the original when end_funcs is falsy)
#   - When end_funcs is empty or falsy, call_graph is returned unchanged
#   - When end_funcs is non-empty, the returned dict contains exactly those FQNs that satisfy both:
#     1. Reachable from entry_func via zero or more edges in call_graph, AND
#     2. Can reach at least one member of end_funcs via zero or more edges in call_graph
#   - For each FQN in the returned dict that is also a member of end_funcs: its callee list is empty (the FQN is a terminal stop-point)
#   - For each FQN in the returned dict that is not a member of end_funcs: its callee list contains exactly the subset of its callees from call_graph that also appear in the returned dict
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _restrict_to_chains(call_graph, entry_func, end_funcs):
    """Keep only functions lying on a call chain from entry_func to an end_func.

    A function is retained iff it is reachable from ``entry_func`` (already
    guaranteed by ``call_graph``) *and* it can reach one of ``end_funcs`` — i.e.
    it sits on some path ``entry_func -> ... -> end_func``. The ``end_funcs`` are
    treated as terminal: their outgoing edges are dropped so chains stop there.

    Args:
        call_graph: dict mapping FQN -> sorted list of callee FQNs, rooted at
            entry_func (as built in _select_functions_by_source).
        entry_func: FQN of the entry point.
        end_funcs: list of FQNs at which to stop. If falsy, call_graph is
            returned unchanged.

    Returns:
        A new call graph (same shape) containing only the on-chain functions.
    """
    if not end_funcs:
        return call_graph

    # Reverse adjacency over the reachable graph.
    callers = {fqn: set() for fqn in call_graph}
    for fqn, callees in call_graph.items():
        for callee in callees:
            callers.setdefault(callee, set()).add(fqn)

    # Nodes that can reach some end_func: reverse-BFS seeded at the end_funcs.
    on_chain = set()
    queue = deque(ef for ef in end_funcs if ef in call_graph)
    while queue:
        fqn = queue.popleft()
        if fqn in on_chain:
            continue
        on_chain.add(fqn)
        for caller in callers.get(fqn, ()):
            if caller not in on_chain:
                queue.append(caller)

    end_set = set(end_funcs)
    pruned = {}
    for fqn in on_chain:
        if fqn in end_set:
            # end_funcs are terminal stop points: no outgoing edges.
            pruned[fqn] = []
        else:
            pruned[fqn] = [c for c in call_graph[fqn] if c in on_chain]
    return pruned
