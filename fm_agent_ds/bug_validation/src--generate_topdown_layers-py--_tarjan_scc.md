# Bug Report: _tarjan_scc

**Source file:** `fm_agent/extracted_functions/src/generate_topdown_layers-py/_tarjan_scc.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of lists, where each inner list is a strongly connected component containing one or more FQN strings drawn from nodes. Every FQN in nodes appears in exactly one inner list across the entire returned outer list. For every edge u  v in edges, the inner list containing u does not appear after the inner list containing v in the returned outer list.

---

### Actual Behavior

The function returns a list L of sets of FQN strings such that:
1. The union of all sets in L equals the set of input `nodes`, and the sets are pairwise disjoint.
2. For every node u in the input nodes and every successor v  edges[u], if the set containing u is different from the set containing v then the index of the set containing v in L is strictly less than the index of the set containing u. Formally, let idx(x) be the position of the set in L that contains x (0-based). Then  u  V,  v  edges[u]: idx(u)  idx(v)  idx(v) < idx(u), where V = set(nodes).
3. Two nodes u and v belong to the same set in L if and only if u can reach v and v can reach u via the directed edges (edges[x] interpreted as successors of x).
The input collections `nodes` and `edges` are not modified. There is no early return or exception raised.

---

## Code Evidence

Line 7: returns "in reverse topological order", Line 42-50: the detection and appending of SCCs that yields reverse topological order, in particular Line 50: `result.append(scc)` adds the components in the wrong order relative to the specification.

---

## Trigger Condition

The specification requires a forward topological order where for an edge uv, u's component appears on or before v's component. The implementation produces reverse topological order (v's component before u's component), and thus fails the ordering requirement for any graph with at least one edge between distinct SCCs. The example above demonstrates the mismatch.

---

## How to trigger the bug

The bug is triggered by calling `_tarjan_scc` on any directed graph with at least one edge between distinct strongly connected components. Tarjan's algorithm produces SCCs in reverse topological order of the condensation DAG, but the specification requires forward topological order (for every edge u→v, u's SCC appears on or before v's SCC).

### Inputs

| Parameter | Value |
|-----------|-------|
| nodes | `['A', 'B', 'C']` |
| edges | `{'A': {'B'}, 'B': {'C'}, 'C': set()}` |

### Expected (spec-correct) Output

`[{'A'}, {'B'}, {'C'}]` — forward topological order (A before B before C)

### Actual (buggy) Output

`[{'C'}, {'B'}, {'A'}]` — reverse topological order (C before B before A)

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '/home/fancy/Projects_Vault/FM-Agent')
from src.generate_topdown_layers import _tarjan_scc

nodes = ['A', 'B', 'C']
edges = {'A': {'B'}, 'B': {'C'}, 'C': set()}

result = _tarjan_scc(nodes, edges)
print(result)
# actual (buggy) output: [{'C'}, {'B'}, {'A'}]
# expected (correct) output: [{'A'}, {'B'}, {'C'}]
```

---

## Probe Script

```python
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
```

### Probe Output

```
CONFIRMED — 2 spec violation(s) in chain A->B->C:
  Edge A->B: idx(A)=2 > idx(B)=1
  Edge B->C: idx(B)=1 > idx(C)=0
  Result (reverse topo order): [{'C'}, {'B'}, {'A'}]
  Expected (forward topo):      [{'A'}, {'B'}, {'C'}]
```
