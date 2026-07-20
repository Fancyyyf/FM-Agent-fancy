# Bug Report: _tarjan_scc

**Source file:** `src/generate_topdown_layers-py/_tarjan_scc.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of sets, each set representing one strongly connected
    component (SCC); the list is ordered in reverse topological order: for any
    directed edge from a node in SCC at position i to a node in SCC at position
    j, i ≤ j (no edge goes from a later SCC in the list to an earlier SCC)
  - Every node in nodes appears in exactly one SCC in the result
  - Each returned SCC is a maximal strongly connected subgraph restricted to
    nodes: for every ordered pair of distinct nodes (u, v) in the same SCC,
    there exists a directed path u → ... → v using only nodes from nodes as
    intermediate vertices, and no proper superset containing that SCC satisfies
    this property while also being a subset of nodes
  - A node that cannot reach any other node in nodes that can also reach it
    back appears as a singleton SCC (a set containing exactly that node)

---

### Actual Behavior

Let V be the set of nodes that are assigned an index in index_map during the traversal, and E = { (u, v) | u ∈ V, v ∈ edges.get(u, set()) if u is a key in edges else set() } ∩ (V × V). The function returns a list result = [S_0, ..., S_{k-1}] where each S_i ⊆ V, the S_i are pairwise disjoint and cover V, each S_i is a strongly connected component (maximal set with mutual reachability via paths in (V,E)), and for all i < j, if ∃ u ∈ S_i, v ∈ S_j with a directed edge from u to v, then i > j (reverse topological order). No side effects persist outside the function; local variables (index_counter, scc_stack, on_stack, index_map, lowlink, call_stack) are discarded.

---

## Code Evidence

Line 87: `result.append(scc)`

---

## Trigger Condition

The code appends SCCs in the order they are discovered (sinks first), producing a reverse topological order where for an edge from SCC at index i to SCC at index j, i > j. The specification requires that for any such edge i ≤ j (an order where edges go from earlier to later indices). The result is not reversed before returning, so any input with cross-SCC edges violates the specification. In the counterexample, the code returns [{2}, {1}], so the edge from 1 to 2 gives i=1, j=0, which fails i ≤ j.

---

## How to trigger the bug

The function uses standard Tarjan's SCC algorithm which naturally produces components in reverse topological order (sinks first). The post-condition in the [SPEC] block incorrectly describes the ordering as i ≤ j (edges go from earlier to later indices), but the implementation produces i > j (edges go from later to earlier indices). The docstring correctly states "in reverse topological order", so either the spec or the docstring/code is wrong — they contradict each other.

### Inputs

| Parameter | Value |
|-----------|-------|
| nodes | `[1, 2]` |
| edges | `{1: {2}, 2: set()}` |

### Expected (spec-correct) Output

A list where for edge 1→2, the index of SCC containing 1 is ≤ the index of SCC containing 2. For example, `[{1}, {2}]` (i=0, j=1, 0 ≤ 1) would satisfy the spec.

### Actual (buggy) Output

`[{2}, {1}]` — edge 1→2 gives i=1, j=0, and 1 ≤ 0 is false.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import _tarjan_scc

nodes = [1, 2]
edges = {1: {2}, 2: set()}

result = _tarjan_scc(nodes, edges)
# actual (buggy) output: [{2}, {1}]
# expected (correct) output per spec: ordering such that i <= j for edge from SCC i to SCC j
# Edge 1→2: i=index_of({1})=1, j=index_of({2})=0; spec requires 1 <= 0 which is False
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on sys.path so that `from src.xxx` resolves
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.generate_topdown_layers import _tarjan_scc

    # Simple DAG: 1 -> 2 (edge from 1 to 2, no cycles)
    # Tarjan produces SCCs in reverse topological order:
    #   Node 2 (sink, no outgoing) processed first  → SCC {2}
    #   Node 1 processed second                     → SCC {1}
    #   Result: [{2}, {1}]
    #
    # Spec claim: for edge from SCC at i to SCC at j, i ≤ j
    # Edge 1→2: i=1 (SCC {1}), j=0 (SCC {2})
    # Spec requires: 1 ≤ 0  →  False
    # Violation → bug confirmed

    nodes = [1, 2]
    edges = {1: {2}, 2: set()}

    actual = _tarjan_scc(nodes, edges)

    # Map node to SCC index in result
    idx_of = {}
    for idx, scc in enumerate(actual):
        for node in scc:
            idx_of[node] = idx

    i = idx_of[1]
    j = idx_of[2]

    # Does the spec hold? Spec requires i <= j for edge 1->2
    spec_holds = i <= j
    # Bug is confirmed if the spec does NOT hold
    bug_reproduced = not spec_holds

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

if bug_reproduced:
    print(f'CONFIRMED — actual result: {actual} | got i={i}, j={j} for edge 1→2 | spec requires i <= j but {i} <= {j} = {spec_holds}')
else:
    print(f'NOT CONFIRMED — spec requirement i <= j was met: {i} <= {j} = {spec_holds}')
```

### Probe Output

```
CONFIRMED — actual result: [{2}, {1}] | got i=1, j=0 for edge 1→2 | spec requires i <= j but 1 <= 0 = False
```
