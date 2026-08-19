# Bug Report: _compute_layers

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/generate_topdown_layers-py/_compute_layers.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of layer dicts sorted by strictly increasing integer `layer` index starting from 0. Each dict contains: `layer` (non-negative integer, 0-indexed), `functions` (sorted list of FQN strings assigned to that layer), and `cycle_resolution` (boolean). Every FQN in phase_fqns appears in exactly one layer across the returned list. For any pair (caller, callee) where both FQNs belong to phase_fqns and the callee is reachable via callees_map, the callee's `layer` index is strictly less than the caller's `layer` index. `cycle_resolution` is false for a layer when every function in that layer was placed without breaking any dependency cycle among phase_fqns members. `cycle_resolution` is true for a layer when at least one function in that layer belongs to a non-trivial strongly connected component (a cycle involving two or more phase_fqns members where each member transitively depends on another in the cycle). When no cycles exist among phase_fqns members, all returned layer dicts have `cycle_resolution` set to false.

---

### Actual Behavior

The variable `layers` is returned. `layers` is a list of dictionaries, each with integer key 'layer' (consecutive from 0), a boolean 'cycle_resolution', and a lexicographically sorted list of strings 'functions'. The union of all 'functions' equals the input set `phase_fqns`; layers 'functions' sets are pairwise disjoint. For any two functions f and g in `phase_fqns` where g  callers_map[f], the layer index of g is  layer index of f; if equal, the layer's 'cycle_resolution' is True. For a layer with 'cycle_resolution' False, no function has a caller within the same layer; all callers of its functions are in strictly earlier layers. In the normal case, every layer with 'cycle_resolution' True is formed from one or more strongly connected components (SCCs) that are mutually reachable via caller edges within the restricted graph, and at least one edge lies inside the layers functions. If the topological sort of SCCs fails (which should not occur for correct Tarjan output), all remaining unassigned functions are placed in a single final layer with 'cycle_resolution' True, which may contain multiple SCCs, but ensures termination. Formally: Let V = set(phase_fqns), E = {(u,v) | v  callers_map[u]  V}. Let L = layers. Then L is a list of records r_i = (layer=i, functions=F_i, cyclic=c_i) where F_i are sorted and disjoint,  F_i = V. For all f,g  V, if g  callers_map[f], let l(f) be the layer index; then l(g)  l(f), and if l(g)=l(f) then c_{l(f)} = True. For any i with c_i = False, for all f  F_i,  g  callers_map[f]  V, l(g) < i. For the normal path: each i with c_i = True is such that the SCCs assigned to layer i form a strongly connected subset of the SCC-DAG, and at least one SCC in the layer has size >1. In the error path, the final layer contains all remaining F and c_|L|-1 = True, possibly breaking the SCC property, but guarantees l(g)  l(f) and c_{layer} = True for equal indices.

---

## Code Evidence

Line 47: for caller_fqn in callers_map.get(fqn, set()) & remaining: (this treats callers as dependencies that must be placed earlier, via the SCC DAG built on lines 48-50 and the topological readiness check on lines 56-59).

---

## Trigger Condition

The code uses callers_map to build a DAG where an SCC's callers must be assigned before the SCC itself, leading to caller layers being lower than callee layers. The specification requires callee layers to be lower than caller layers. Thus any input with at least one call edge yields a mismatch.

---

## How to trigger the bug

The function `_compute_layers` uses `callers_map` (instead of `callees_map`) to determine readiness for layer assignment. A function is considered "ready" only when all its same-phase callers have already been assigned, which places callers in lower-numbered layers than callees. The specification requires the opposite: callees must be in strictly lower-numbered layers than their callers.

### Inputs

| Parameter | Value |
|-----------|-------|
| phase_fqns | `["A", "B"]` |
| callees_map | `{"A": {"B"}}` (A calls B) |
| callers_map | `{"B": {"A"}}` (B is called by A) |

### Expected (spec-correct) Output

B (callee) in layer 0, A (caller) in layer 1:
```json
[{"layer": 0, "functions": ["B"], "cycle_resolution": false}, {"layer": 1, "functions": ["A"], "cycle_resolution": false}]
```

### Actual (buggy) Output

A (caller) in layer 0, B (callee) in layer 1:
```json
[{"layer": 0, "functions": ["A"], "cycle_resolution": false}, {"layer": 1, "functions": ["B"], "cycle_resolution": false}]
```

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from src.generate_topdown_layers import _compute_layers

phase_fqns = ["A", "B"]
callees_map = {"A": {"B"}}
callers_map = {"B": {"A"}}

layers = _compute_layers(phase_fqns, callees_map, callers_map)
# actual (buggy) output: caller A at layer 0, callee B at layer 1
# expected (correct) output: callee B at layer 0, caller A at layer 1
```

---

## Probe Script

```python
import sys
import os

# Ensure the repo root is on the path for the entry-point import
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)

try:
    from src.generate_topdown_layers import _compute_layers

    # Minimal test: A calls B
    # callees_map: A -> {B}   (A calls B)
    # callers_map: B -> {A}   (B is called by A)
    phase_fqns = ["A", "B"]
    callees_map = {"A": {"B"}}
    callers_map = {"B": {"A"}}

    actual = _compute_layers(phase_fqns, callees_map, callers_map)

    # Extract fqn -> layer assignments
    actual_assignments = {}
    for layer_info in actual:
        for fqn in layer_info["functions"]:
            actual_assignments[fqn] = layer_info["layer"]

    caller_layer = actual_assignments["A"]
    callee_layer = actual_assignments["B"]

    # Spec claim: callee's layer is STRICTLY LESS than caller's layer
    # i.e., for edge A -> B: B.layer < A.layer
    # Bug: code uses callers_map, so caller gets assigned first
    # Bug confirmed if callee.layer >= caller.layer
    bug_exists = callee_layer >= caller_layer

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

if bug_exists:
    print(
        f"CONFIRMED — caller A at layer {caller_layer}, callee B at layer {callee_layer} "
        f"(callee_layer >= caller_layer, but spec requires callee_layer < caller_layer)"
    )
else:
    print(
        f"NOT CONFIRMED — callee B at layer {callee_layer}, caller A at layer {caller_layer} "
        f"(callee_layer < caller_layer as spec requires)"
    )
```

### Probe Output

```
CONFIRMED — caller A at layer 0, callee B at layer 1 (callee_layer >= caller_layer, but spec requires callee_layer < caller_layer)
```
