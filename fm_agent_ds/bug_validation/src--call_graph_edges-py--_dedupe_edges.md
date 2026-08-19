# Bug Report: _dedupe_edges

**Source file:** `/home/fancy/Projects_Vault/FM-Agent/fm_agent/extracted_functions/src/call_graph_edges-py/_dedupe_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a list of CallEdge objects where no two entries share the same caller fully-qualified name and callee fully-qualified name. For entries with the same caller FQN and callee FQN, the returned entry contains the union of all distinct callsite_names and the union of all distinct info_names from all occurrences of that pair, and takes the source from the first occurrence. The relative order of first occurrences of each unique (caller.fqn, callee.fqn) pair is preserved.

---

### Actual Behavior

The function returns a list of CallEdge objects with no duplicate (caller.fqn, callee.fqn) pairs. For each distinct pair (A, B) present in the input edges, exactly one CallEdge r appears in the result, such that r.caller.fqn == A, r.callee.fqn == B, r.source is the source of the first input edge with that pair, r.caller.callsite_names is a tuple containing each distinct callsite name from all input edges with that pair, in the order of first occurrence (original order from the first edge, then new names from subsequent edges appended), and r.callee.info_names is a tuple containing each distinct info name from all input edges with that pair, similarly ordered. The output list is sorted in ascending lexicographic order by (caller.fqn, callee.fqn). No input objects are modified. Formally: Let E = list(edges) be the sequence of CallEdge objects consumed. Let K = {(e.caller.fqn, e.callee.fqn) | e  E}. For each k = (f1, f2)  K, let E_k = [e  E | e.caller.fqn = f1  e.callee.fqn = f2] in the order they appear. The returned list R has one element r per k, and sorting of R satisfies that for any r_i, r_j with keys k_i, k_j, r_i precedes r_j iff k_i < k_j lexicographically. For each such r: r.caller.fqn = f1; r.callee.fqn = f2; r.source = E_k[0].source; let flat_callsite_names = concatenation of (e.caller.callsite_names for e in E_k) preserving order; then r.caller.callsite_names = tuple(ordered unique elements of flat_callsite_names by first appearance). Similarly, let flat_info_names = concatenation of (e.callee.info_names for e in E_k); then r.callee.info_names = tuple(ordered unique elements of flat_info_names by first appearance).

---

## Code Evidence

Line 23: for (_caller_fqn, callee_fqn), data in sorted(merged.items()):

---

## Trigger Condition

The specification requires preserving the relative order of first occurrences of each unique (caller.fqn, callee.fqn) pair. The code uses sorted(), which reorders the pairs in ascending lexicographic order, violating the required ordering for any input where the first-occurrence order differs from the sorted order.

---

## How to trigger the bug

When `_dedupe_edges` receives a sequence of CallEdge objects whose (caller.fqn, callee.fqn) pairs first appear in an order that differs from lexicographic sort, the function returns the deduplicated edges in lexicographic order instead of preserving the original first-occurrence order.

### Inputs

| Parameter | Value |
|-----------|-------|
| edges[0] | CallEdge(caller.fqn="B::func", callee.fqn="B::callee", callsite_names=["b_callsite"], info_names=["b_info"]) |
| edges[1] | CallEdge(caller.fqn="A::func", callee.fqn="A::callee", callsite_names=["a_callsite"], info_names=["a_info"]) |
| edges[2] | CallEdge(caller.fqn="C::func", callee.fqn="A::callee", callsite_names=["c_callsite"], info_names=["c_info"]) |
| edges[3] | CallEdge(caller.fqn="B::func", callee.fqn="B::callee", callsite_names=["b_callsite_2"], info_names=["b_info_2"]) (duplicate of first edge, merged) |

### Expected (spec-correct) Output

First-occurrence order preserved after deduplication:

```
[("B::func", "B::callee"), ("A::func", "A::callee"), ("C::func", "A::callee")]
```

The merged B→B edge contains callsite_names=("b_callsite", "b_callsite_2") and info_names=("b_info", "b_info_2") with source from the first edge.

### Actual (buggy) Output

Sorted lexicographically by (caller.fqn, callee.fqn):

```
[("A::func", "A::callee"), ("B::func", "B::callee"), ("C::func", "A::callee")]
```

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, os, tempfile
from src.call_graph_edges import load_call_edges

edges_data = {
    "edges": [
        {"caller": {"fqn": "B::func", "callsite_names": ["b_callsite"]},
         "callee": {"fqn": "B::callee", "info_names": ["b_info"]}},
        {"caller": {"fqn": "A::func", "callsite_names": ["a_callsite"]},
         "callee": {"fqn": "A::callee", "info_names": ["a_info"]}},
        {"caller": {"fqn": "C::func", "callsite_names": ["c_callsite"]},
         "callee": {"fqn": "A::callee", "info_names": ["c_info"]}},
        {"caller": {"fqn": "B::func", "callsite_names": ["b_callsite_2"]},
         "callee": {"fqn": "B::callee", "info_names": ["b_info_2"]}},
    ]
}

tmpdir = tempfile.mkdtemp()
edge_file = os.path.join(tmpdir, "edges.json")
with open(edge_file, "w") as f:
    json.dump(edges_data, f)

result = load_call_edges(edge_file)
print([(e.caller.fqn, e.callee.fqn) for e in result])
# actual (buggy) output: [('A::func', 'A::callee'), ('B::func', 'B::callee'), ('C::func', 'A::callee')]
# expected (correct) output: [('B::func', 'B::callee'), ('A::func', 'A::callee'), ('C::func', 'A::callee')]
```

---

## Probe Script

```python
"""Probe script for bug: src--call_graph_edges-py--_dedupe_edges

The _dedupe_edges() function uses sorted(merged.items()), which reorders output
by lexicographic (caller.fqn, callee.fqn) instead of preserving the relative
order of first occurrences as the specification requires.
"""

import json
import os
import shutil
import sys
import tempfile

try:
    from src.call_graph_edges import load_call_edges

    edges_data = {
        "edges": [
            {
                "caller": {"fqn": "B::func", "callsite_names": ["b_callsite"]},
                "callee": {"fqn": "B::callee", "info_names": ["b_info"]},
            },
            {
                "caller": {"fqn": "A::func", "callsite_names": ["a_callsite"]},
                "callee": {"fqn": "A::callee", "info_names": ["a_info"]},
            },
            {
                "caller": {"fqn": "C::func", "callsite_names": ["c_callsite"]},
                "callee": {"fqn": "A::callee", "info_names": ["c_info"]},
            },
            {
                "caller": {"fqn": "B::func", "callsite_names": ["b_callsite_2"]},
                "callee": {"fqn": "B::callee", "info_names": ["b_info_2"]},
            },
        ]
    }

    tmpdir = tempfile.mkdtemp(prefix="bug_dedupe_")
    edge_file = os.path.join(tmpdir, "edges.json")
    try:
        with open(edge_file, "w") as f:
            json.dump(edges_data, f)

        result = load_call_edges(edge_file)

        actual_order = [(e.caller.fqn, e.callee.fqn) for e in result]

        expected_spec = [
            ("B::func", "B::callee"),
            ("A::func", "A::callee"),
            ("C::func", "A::callee"),
        ]

        expected_buggy = [
            ("A::func", "A::callee"),
            ("B::func", "B::callee"),
            ("C::func", "A::callee"),
        ]

        bug_reproduced = actual_order != expected_spec

        if bug_reproduced and actual_order == expected_buggy:
            print(
                "CONFIRMED — actual (sorted by key):",
                actual_order,
                "| expected (first-occurrence):",
                expected_spec,
            )
        elif not bug_reproduced:
            print(
                "NOT CONFIRMED — actual matched spec (first-occurrence order preserved):",
                actual_order,
            )
        else:
            print(
                "NOT CONFIRMED — actual order:",
                actual_order,
                "| expected by spec:",
                expected_spec,
                "| expected by bug:",
                expected_buggy,
            )

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

except Exception:
    import traceback

    traceback.print_exc()
    print("ERROR: probe script failed with an unhandled exception")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — actual (sorted by key): [('A::func', 'A::callee'), ('B::func', 'B::callee'), ('C::func', 'A::callee')] | expected (first-occurrence): [('B::func', 'B::callee'), ('A::func', 'A::callee'), ('C::func', 'A::callee')]
```
