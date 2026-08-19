# Bug Report: _restrict_to_chains

**Source file:** `src/entry_reasoning_pipeline.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

When end_funcs is falsy, returns call_graph unchanged. When end_funcs is non-empty, returns a new dict with the same shape as call_graph (FQN keys mapping to lists of callee FQN strings) containing only functions that lie on at least one directed path from entry_func to any FQN in end_funcs within call_graph. For each such function, only callees that also lie on at least one such path are retained. Functions whose FQN appears in end_funcs have empty callee lists in the returned dict regardless of their original callees. The relative order of callees in each list is preserved from call_graph. The original call_graph is unmodified.

---

### Actual Behavior

If `end_funcs` is falsy, the function returns `call_graph` unchanged. If `end_funcs` is truthy but not iterable, a `TypeError` is raised. Otherwise (truthy and iterable), let `EF = {e | end_funcs | e ∈ keys(call_graph)}` and let `on_chain` be the set of all functions `v` in `keys(call_graph)` that can reach at least one element of `EF` via a directed path in `call_graph`. The function returns a new dictionary `pruned` with `keys(pruned) = on_chain`. For each `v ∈ on_chain`: if `v ∈ EF` then `pruned[v] = []`, else `pruned[v] = [c for c in call_graph[v] if c ∈ on_chain]`. The input `call_graph` is not mutated. The parameter `entry_func` is not used in the computation. Formally:

Let `reach(v)` be the set of nodes reachable from `v` via the directed edges of `call_graph`.
If `not end_funcs`: result = call_graph.
Else if `end_funcs` is not iterable: raise TypeError.
Else:
  EF = set(end_funcs) ∩ keys(call_graph)
  on_chain = { v ∈ keys(call_graph) | reach(v) ∩ EF ≠ ∅ }
  result = { v : [] if v ∈ EF else [c ∈ call_graph[v] | c ∈ on_chain] | v ∈ on_chain }

---

## Code Evidence

Line 24: on_chain = set()
Line 25: queue = deque(ef for ef in end_funcs if ef in call_graph)
Line 26: while queue:
Line 27:     fqn = queue.popleft()
Line 28:     if fqn in on_chain:
Line 29:         continue
Line 30:     on_chain.add(fqn)
Line 31:     for caller in callers.get(fqn, ()):
Line 32:         if caller not in on_chain:
Line 33:             queue.append(caller)

---

## Trigger Condition

The specification requires that only functions on a path from entry_func to an end_func are retained. The code computes on_chain solely by reverse reachability from end_funcs, without checking reachability from entry_func. In a call_graph containing a disconnected component (nodes not reachable from entry_func) that can still reach an end_func, those disconnected nodes are incorrectly included in the output, violating the specification.

---

## How to trigger the bug

A call_graph where function "D" calls end_func "C" but is NOT reachable from entry_func "A" causes D to be incorrectly included in the result. The code only checks reverse reachability from end_funcs (i.e., who can reach C?), ignoring forward reachability from entry_func (i.e., is D reachable from A?).

### Inputs

| Parameter | Value |
|-----------|-------|
| call_graph | `{"A": ["B"], "B": ["C"], "C": [], "D": ["C"]}` |
| entry_func | `"A"` |
| end_funcs | `["C"]` |

### Expected (spec-correct) Output

`{"A": ["B"], "B": ["C"], "C": []}`

### Actual (buggy) Output

`{"A": ["B"], "B": ["C"], "C": [], "D": ["C"]}`

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.entry_reasoning_pipeline import _restrict_to_chains

call_graph = {
    "A": ["B"],
    "B": ["C"],
    "C": [],
    "D": ["C"],
}
result = _restrict_to_chains(call_graph, "A", ["C"])
# actual (buggy) output: {'A': ['B'], 'B': ['C'], 'C': [], 'D': ['C']}
# expected (correct) output: {'A': ['B'], 'B': ['C'], 'C': []}
print(result)
```

---

## Probe Script

```python
import sys
import os
import tempfile

# Ensure the repo root is on sys.path so 'from src...' resolves.
# Python 3 adds the script's directory as sys.path[0], not the CWD,
# when the script path contains a directory component.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from src.entry_reasoning_pipeline import _restrict_to_chains
except Exception as e:
    print(f'ERROR: import failed: {e}')
    sys.exit(1)

# Build a call_graph where D is NOT reachable from entry_func "A",
# but D CAN reach end_func "C" (via D -> C).
# The spec requires only functions on a directed path FROM entry_func TO end_func
# to be retained. The buggy code only checks reverse reachability from end_funcs
# and ignores entry_func entirely, so D is incorrectly included.
# Every FQN must be a key in call_graph (the spec says "FQN keys mapping to lists
# of callee FQN strings"). C must be a key so it passes the `ef in call_graph`
# filter on line 30, and D must be a key so the reverse adjacency loop visits it.
call_graph = {
    "A": ["B"],
    "B": ["C"],
    "C": [],       # end_func target — no outgoing edges
    "D": ["C"],    # D not reachable from A, but CAN reach C
}
entry_func = "A"
end_funcs = ["C"]

# Use a fresh temp dir as the probe workspace (FM-Agent self-validation guard).
tmpdir = tempfile.mkdtemp(prefix="probe_restrict_to_chains_")
os.chdir(tmpdir)  # isolate file I/O from repo

try:
    actual = _restrict_to_chains(call_graph, entry_func, end_funcs)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)

# Expected (spec-correct): only functions on A -> ... -> C chain.
# That is A, B, C. D is NOT reachable from A, so D should NOT appear.
expected = {"A": ["B"], "B": ["C"], "C": []}

# The bug is confirmed if D (not on A->C path) appears in the output.
passed = "D" in actual

if passed:
    print(f'CONFIRMED — D incorrectly included in output: actual={actual!r} | expected (spec)=no D')
else:
    print(f'NOT CONFIRMED — actual matched expected: {actual!r}')
```

### Probe Output

```
CONFIRMED — D incorrectly included in output: actual={'A': ['B'], 'B': ['C'], 'C': [], 'D': ['C']} | expected (spec)=no D
```
