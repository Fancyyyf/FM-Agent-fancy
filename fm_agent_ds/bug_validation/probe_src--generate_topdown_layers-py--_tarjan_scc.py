#!/usr/bin/env python3
"""Probe for bug: _tarjan_scc returns reverse topological order instead of forward.

Spec claim: for every edge u->v, u's SCC appears on or before v's SCC.
Tarjan's algorithm returns reverse topological order of the condensation DAG,
so u's SCC (callee) appears AFTER v's SCC (caller) in the result list.
"""
import sys

sys.path.insert(0, '/home/fancy/Projects_Vault/FM-Agent')

try:
    from src.generate_topdown_layers import _tarjan_scc

    # ── Test 1: simple chain A → B → C ───────────────────────────────
    # Forward topo (spec): A before B before C → [{A}, {B}, {C}]
    # Tarjan reverse topo : C before B before A → [{C}, {B}, {A}]  (BUG)
    nodes = ['A', 'B', 'C']
    edges = {'A': {'B'}, 'B': {'C'}, 'C': set()}

    result = _tarjan_scc(nodes, edges)

    idx = {}
    for i, scc in enumerate(result):
        for node in scc:
            idx[node] = i

    violations = []
    for u, successors in edges.items():
        for v in successors:
            if idx.get(u, -1) > idx.get(v, -1):
                violations.append((u, v, idx[u], idx[v]))

    if violations:
        print(f'CONFIRMED — {len(violations)} spec violation(s) in chain A->B->C:')
        for u, v, ui, vi in violations:
            print(f'  Edge {u}->{v}: idx({u})={ui} > idx({v})={vi}')
        print(f'  Result (reverse topo order): {result!r}')
        print(f'  Expected (forward topo):      [{{\'A\'}}, {{\'B\'}}, {{\'C\'}}]')
    else:
        print(f'NOT CONFIRMED — all edges satisfy spec. Result: {result!r}')

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {e}')
    sys.exit(1)
