# Bug Report: _compute_layers

**Source file:** `/tmp/fm_agent_wt_FM-Agent_dlsr6ukl/snapshot/fm_agent/extracted_functions/src/generate_topdown_layers-py/_compute_layers.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list of layer dicts, sorted by ascending "layer" (0-indexed integer)
  - Each layer dict contains: "layer" (int), "functions" (list of FQNs in lexicographic order), and "cycle_resolution" (bool)
  - Every FQN in phase_fqns appears in exactly one layer's "functions" list
  - For every directed edge (caller  callee) where both endpoints are in phase_fqns: the callee's layer index is less than or equal to the caller's layer index
  - Equality (callee and caller in the same layer) occurs only when the two functions belong to the same strongly connected component (mutual recursion), and the layer is marked with "cycle_resolution": true
  - "cycle_resolution" is true when the layer contains at least one SCC with two or more members; it is false when all SCCs in the layer are singletons (no mutual recursion resolved)
  - When no cycles exist, layers are assigned by applying Kahn's algorithm on the caller graph: a function enters the current layer when all its in-phase callers have already been assigned to strictly earlier layers

---

### Actual Behavior

After execution, the function returns the list `layers`. The inputs `phase_fqns`, `callees_map`, and `callers_map` are not mutated. No exceptions are raised. Let `Phase` = set(phase_fqns), `C` = callees_map, and let `G` be the directed graph with vertices `Phase` and edge (u  v) if v  C.get(u, []). Then:
1. `layers` is a list of dictionaries, each with keys 'layer' (int), 'functions' (list of strings sorted lexicographically), and 'cycle_resolution' (bool).
2. For i from 0 to |layers|-1: layers[i]['layer'] == i.
3. The sets { f for l in layers for f in l['functions'] } form a partition of `Phase`: every FQN in `Phase` appears in exactly one layer's 'functions' list.
4. For any distinct a, b  Phase, if b  C.get(a, []) then let l_a, l_b be the indices of the layers containing a and b, respectively. We have l_a  l_b.
5. If l_a == l_b, then the layer has cycle_resolution == True and a and b are in the same strongly connected component (SCC) of G (i.e., there is a directed cycle containing both).
6. If a layer has cycle_resolution == False, then every SCC of G that is included in that layer has size 1 (no nontrivial cycles) and thus for any distinct a,b in that layer, we have l_a < l_b whenever a calls b.
7. Every SCC of G is entirely contained in a single layer, and layers are formed by topologically sorting the SCC DAG: if SCC A has an edge to SCC B (A calls B), then A's layer index  B's layer index, with equality only if both are in the same layer (which implies cycle_resolution == True).

---

## Code Evidence

Line 46:                 scc_i = fqn_to_scc[fqn]
Line 47:                 for caller_fqn in callers_map.get(fqn, set()) & remaining:
Line 48:                     scc_j = fqn_to_scc[caller_fqn]
Line 49:                     if scc_i != scc_j:
Line 50:                         scc_callers[scc_i].add(scc_j)
Line 56:                 for scc_idx in scc_remaining:
Line 57:                     unassigned_scc_callers = scc_callers.get(scc_idx, set()) - set(scc_assigned.keys())
Line 58:                     if not unassigned_scc_callers:
Line 59:                         scc_ready.add(scc_idx)

---

## Trigger Condition

The code assigns layer indices in reverse topological order, yielding layer(caller) < layer(callee) for any call edge. The specification requires callee's layer <= caller's layer. With A calling B, the code produces layers [{layer:0, functions:['A']}, {layer:1, functions:['B']}]; the specification demands callee B at layer 0 and caller A at layer 1. The topological sort using callers_map puts top-level callers first, violating the required order.

---

## How to trigger the bug

The `_compute_layers` function uses Kahn's algorithm with `callers_map` to determine layer readiness: a function is ready for the current layer when all its in-phase callers have been assigned. This produces `layer(caller) < layer(callee)`. The specification requires `layer(callee) <= layer(caller)` — callees must be assigned to equal or earlier layers than their callers.

### Inputs

| Parameter | Value |
|-----------|-------|
| `phase_fqns` | `{"A", "B"}` |
| `callees_map` | `{"A": {"B"}}` (A calls B) |
| `callers_map` | `{"B": {"A"}}` (A calls B) |

### Expected (spec-correct) Output

B (the callee) at layer 0, A (the caller) at layer 1: `[{"layer": 0, "functions": ["B"], "cycle_resolution": false}, {"layer": 1, "functions": ["A"], "cycle_resolution": false}]`

### Actual (buggy) Output

A (the caller, has no unassigned callers) at layer 0, B (the callee) at layer 1: `[{"layer": 0, "functions": ["A"], "cycle_resolution": false}, {"layer": 1, "functions": ["B"], "cycle_resolution": false}]`

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
sys.path.insert(0, '.')
from src.generate_topdown_layers import _compute_layers

phase_fqns = {"A", "B"}
callees_map = {"A": {"B"}}  # A calls B
callers_map = {"B": {"A"}}  # A calls B

layers = _compute_layers(phase_fqns, callees_map, callers_map)
for l in layers:
    print(l)
# actual (buggy) output:
# {'layer': 0, 'functions': ['A'], 'cycle_resolution': False}
# {'layer': 1, 'functions': ['B'], 'cycle_resolution': False}
# expected (correct) output:
# {'layer': 0, 'functions': ['B'], 'cycle_resolution': False}
# {'layer': 1, 'functions': ['A'], 'cycle_resolution': False}
```

---

## Probe Script

```python
"""Probe script for _compute_layers bug: topological layer ordering is reversed.

The spec requires layer(callee) <= layer(caller), but the code produces
layer(caller) < layer(callee) because it uses callers_map (instead of
callees_map) in Kahn's algorithm.
"""
import sys
sys.path.insert(0, '.')

from src.generate_topdown_layers import _compute_layers

# Simple DAG: A calls B
#   A ──→ B
# Spec requires: callee B at layer 0, caller A at layer 1
# Code produces: caller A at layer 0, callee B at layer 1 (reversed)
phase_fqns = {"A", "B"}
callees_map = {"A": {"B"}}  # A calls B
callers_map = {"B": {"A"}}  # A calls B

try:
    layers = _compute_layers(phase_fqns, callees_map, callers_map)

    # Find where A and B ended up
    a_layer = b_layer = None
    for layer_info in layers:
        if "A" in layer_info["functions"]:
            a_layer = layer_info["layer"]
        if "B" in layer_info["functions"]:
            b_layer = layer_info["layer"]

    # Spec says callee (B) <= caller (A), but code gives caller (A) < callee (B)
    # Bug is confirmed if caller's layer < callee's layer (wrong order)
    spec_violation = a_layer is not None and b_layer is not None and a_layer < b_layer

    if spec_violation:
        print(f'CONFIRMED — caller A at layer {a_layer}, callee B at layer {b_layer} '
              f'(spec requires callee layer <= caller layer)')
    else:
        print(f'NOT CONFIRMED — A at layer {a_layer}, B at layer {b_layer} '
              f'(caller-callee ordering matches spec)')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — caller A at layer 0, callee B at layer 1 (spec requires callee layer <= caller layer)
```
