# Bug Report: _restrict_to_chains

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- call_graph is never mutated; a new dict is returned (or the original when end_funcs is falsy)
  - When end_funcs is empty or falsy, call_graph is returned unchanged
  - When end_funcs is non-empty, the returned dict contains exactly those FQNs that satisfy both:
    1. Reachable from entry_func via zero or more edges in call_graph, AND
    2. Can reach at least one member of end_funcs via zero or more edges in call_graph
  - For each FQN in the returned dict that is also a member of end_funcs: its callee list is empty (the FQN is a terminal stop-point)
  - For each FQN in the returned dict that is not a member of end_funcs: its callee list contains exactly the subset of its callees from call_graph that also appear in the returned dict

---

### Actual Behavior

If `bool(end_funcs)` is False, the return value is the input dictionary `call_graph` unchanged (identical reference). Otherwise, let `V` be the set of keys in `call_graph`, and for each `u  V`, let `E(u) = call_graph[u]`. Let `T = {t  end_funcs | t  V}` be the end_funcs present in the graph. Define `R = { u  V | there exists a directed path from u to some t  T }` (nodes that can reach an end_func). The returned dictionary `pruned` satisfies: (1) `set(pruned.keys()) = R`; (2) for every `u  R`, if `u  T` then `pruned[u] = []`, else `pruned[u] = [v for v in E(u) if v  R]`. The original `call_graph` is assumed to contain only nodes reachable from `entry_func`; therefore `R` is exactly the set of functions lying on some call chain from `entry_func` to an end_func, and those chains are preserved in `pruned` up to the terminal end_func nodes (which have no outgoing edges).

---

## Code Evidence

Line 25: queue = deque(ef for ef in end_funcs if ef in call_graph)
Line 31: for caller in callers.get(fqn, ()):
Line 41: pruned[fqn] = [c for c in call_graph[fqn] if c in on_chain]

---

## Trigger Condition

The code only checks backward reachability to end_funcs (reverse BFS from end_funcs) and does not verify forward reachability from entry_func. In the counterexample, nodes 'D' and 'E' are not reachable from 'A' but can reach 'C', so they are incorrectly included in the output, violating the specification which requires nodes to be both reachable from entry_func and able to reach an end_func.

---

## How to trigger the bug

A call_graph is constructed where node `E` calls `C` (an end_func) but `E` is not reachable from `A` (entry_func). The reverse BFS from `C` discovers `E` as a caller and includes it in the output, even though `E` fails the forward-reachability requirement.

### Inputs

| Parameter | Value |
|-----------|-------|
| call_graph | `{'A': ['B'], 'B': ['C'], 'C': ['D'], 'D': [], 'E': ['C']}` |
| entry_func | `'A'` |
| end_funcs | `['C']` |

### Expected (spec-correct) Output

`{'A': ['B'], 'B': ['C'], 'C': []}` — only A, B, C (nodes both reachable from A AND able to reach C)

### Actual (buggy) Output

`{'A': ['B'], 'B': ['C'], 'C': [], 'E': ['C']}` — E is incorrectly included

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```py
import sys
sys.path.insert(0, '.')
from src.entry_reasoning_pipeline import _restrict_to_chains

call_graph = {
    'A': ['B'],
    'B': ['C'],
    'C': ['D'],
    'D': [],
    'E': ['C'],
}
entry_func = 'A'
end_funcs = ['C']

result = _restrict_to_chains(call_graph, entry_func, end_funcs)
print(result)
# actual (buggy) output: {'B': ['C'], 'E': ['C'], 'A': ['B'], 'C': []}
# expected (correct) output: {'B': ['C'], 'A': ['B'], 'C': []}
```

---

## Probe Script

```py
"""Probe script for bug: _restrict_to_chains includes nodes not reachable from entry_func.

The function only does reverse BFS from end_funcs but never verifies forward
reachability from entry_func. Nodes not reachable from entry_func that can reach
an end_func are incorrectly included in the output.
"""
import sys
import os

# The probe is at fm_agent/bug_validation/probe_*.py, so three dirs up is the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.entry_reasoning_pipeline import _restrict_to_chains

# Counterexample call graph:
#   A -> B -> C -> D
#   E -> C           (E is NOT reachable from A)
# With entry_func='A' and end_funcs=['C']:
#   Spec requires: only nodes on paths A -> ... -> C -> {A, B, C}
#   Buggy code includes E because reverse BFS from C finds E as a caller,
#   without checking whether E is reachable from A.
call_graph = {
    'A': ['B'],
    'B': ['C'],
    'C': ['D'],
    'D': [],
    'E': ['C'],  # E can reach C but is NOT reachable from A
}
entry_func = 'A'
end_funcs = ['C']

# Spec-correct expected output: nodes must satisfy BOTH
#   1. Reachable from entry_func (A -> ... -> node exists in call_graph)
#   2. Can reach an end_func (node -> ... -> C exists in call_graph)
# Only A, B, C satisfy both. E satisfies (2) but NOT (1).
expected_keys = {'A', 'B', 'C'}

try:
    result = _restrict_to_chains(call_graph, entry_func, end_funcs)
    actual_keys = set(result.keys())

    # The bug: E should NOT be present
    passed = actual_keys != expected_keys

    if passed:
        extra = actual_keys - expected_keys
        missing = expected_keys - actual_keys
        details = []
        if extra:
            details.append(f"extra (incorrectly included): {sorted(extra)!r}")
        if missing:
            details.append(f"missing (incorrectly excluded): {sorted(missing)!r}")
        print(f"CONFIRMED - {', '.join(details)}")
        print(f"  actual keys:   {sorted(actual_keys)!r}")
        print(f"  expected keys: {sorted(expected_keys)!r}")
        print(f"  full result:   {result!r}")
    else:
        print(f"NOT CONFIRMED - actual matched expected: {sorted(actual_keys)!r}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
```

### Probe Output

```
CONFIRMED - extra (incorrectly included): ['E']
  actual keys:   ['A', 'B', 'C', 'E']
  expected keys: ['A', 'B', 'C']
  full result:   {'B': ['C'], 'E': ['C'], 'A': ['B'], 'C': []}
```
