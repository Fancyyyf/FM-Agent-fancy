# Bug Report: _dedupe_edges

**Source file:** `src/call_graph_edges.py`
**Verdict:** MISMATCH
**Confirmation status:** confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

- Returns a list containing exactly one occurrence of each distinct CallEdge present in
    edges, preserving the relative order of first occurrences

---

### Actual Behavior

Natural language: The function returns a sorted list of CallEdge objects with unique (caller.fqn, callee.fqn) pairs from the input. The list is sorted in ascending order by (caller.fqn, callee.fqn). For each unique pair, the returned CallEdge has caller.fqn equal to the common caller FQN, callee.fqn equal to the common callee FQN, source from the first edge with that pair in iteration order, caller.callsite_names a tuple of all distinct callsite_names across edges with that pair in order of first appearance, and callee.info_names a tuple of all distinct info_names across edges with that pair in order of first appearance. The function has no side effects. Formal logic: Let E be the sequence of input edges in iteration order. Define K = { (e.caller.fqn, e.callee.fqn) : e in E }. For each k in K, let E_k be the subsequence of edges with that key. Then result is a list of length |K|, sorted by k lexicographically. For each k = (c_fqn, t_fqn) in K, there is a unique element r in result such that: r.caller.fqn = c_fqn, r.callee.fqn = t_fqn, r.source = first(E_k).source, r.caller.callsite_names = tuple(ordered_unique(concat_{e in E_k} e.caller.callsite_names)), r.callee.info_names = tuple(ordered_unique(concat_{e in E_k} e.callee.info_names)), where ordered_unique returns a list preserving the first occurrence of each element.

---

## Code Evidence

Line 4: key = (
            edge.caller.fqn,
            edge.callee.fqn,
        )
Line 8: if key not in merged:
Line 23: for (_caller_fqn, callee_fqn), data in sorted(merged.items()):

---

## Trigger Condition

The specification requires returning each distinct CallEdge exactly once, preserving the relative order of first occurrences. The code deduplicates only by (caller.fqn, callee.fqn) and merges callsite_names and info_names from all edges with the same key, producing a single entry that discards differing source values and combines attributes. Additionally, it sorts the result by (caller.fqn, callee.fqn) instead of preserving input order. The counterexample shows two distinct edges (different source and attribute tuples) that share the same FQN pair; the code incorrectly merges them and loses the second edge.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| Edge 1 | caller.fqn=`mod::func_a`, callee.fqn=`mod::func_b`, source=`source_A`, callsite_names=`("site1",)`, info_names=`("info1",)` |
| Edge 2 | caller.fqn=`mod::func_a`, callee.fqn=`mod::func_b`, source=`source_B`, callsite_names=`("site2",)`, info_names=`("info2",)` |

### Expected (spec-correct) Output

A list of **2** `CallEdge` objects, in input order, each preserving its own `source`, `callsite_names`, and `info_names`.

### Actual (buggy) Output

A list of **1** `CallEdge` object, with `source` = `"source_A"` (from the first edge), merged `callsite_names` = `("site1", "site2")`, merged `info_names` = `("info1", "info2")`.

### How to Reproduce

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
import json, tempfile, os
from src.call_graph_edges import load_call_edges

tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
json.dump({
    "edges": [
        {
            "caller": {"fqn": "mod::func_a", "callsite_names": ["site1"]},
            "callee": {"fqn": "mod::func_b", "info_names": ["info1"]},
            "source": "source_A",
        },
        {
            "caller": {"fqn": "mod::func_a", "callsite_names": ["site2"]},
            "callee": {"fqn": "mod::func_b", "info_names": ["info2"]},
            "source": "source_B",
        },
    ]
}, tmp)
tmp.close()

result = load_call_edges(tmp.name)
print(len(result))  # actual (buggy) output: 1
# expected (correct) output: 2
os.unlink(tmp.name)
```

---

## Probe Script

```python
"""Probe script for _dedupe_edges bug: edges with same FQN pair but different
source/attributes get incorrectly merged into one, and result is sorted
instead of preserving input order."""
import json
import os
import sys
import tempfile

# Ensure repo root is on the path so "src" is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

try:
    from src.call_graph_edges import load_call_edges, CallEdge, CallerSelector, CalleeTarget

    # Build a temporary JSON file with two edges that share the same
    # (caller.fqn, callee.fqn) key but differ in source, callsite_names,
    # and info_names.  The spec says these are distinct CallEdge objects
    # and both should appear in the output in input order.  The buggy code
    # merges them into a single entry and sorts the output.
    edges_payload = {
        "edges": [
            {
                "caller": {"fqn": "mod::func_a", "callsite_names": ["site1"]},
                "callee": {"fqn": "mod::func_b", "info_names": ["info1"]},
                "source": "source_A",
            },
            {
                "caller": {"fqn": "mod::func_a", "callsite_names": ["site2"]},
                "callee": {"fqn": "mod::func_b", "info_names": ["info2"]},
                "source": "source_B",
            },
        ]
    }

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    tmp_path = tmp.name
    json.dump(edges_payload, tmp)
    tmp.close()

    try:
        result = load_call_edges(tmp_path)

        expected_count = 2  # two distinct CallEdge objects (different sources)
        actual_count = len(result)

        # Also verify the spec claim about preserving input order.
        # Buggy code sorts by (caller.fqn, callee.fqn) — if we reverse
        # the order here (B then A), sorted output would flip them.
        # But the primary reproduction check is the merge: 2 edges → 1 edge.
        if actual_count != expected_count:
            print(
                f"CONFIRMED — got {actual_count} edges (expected {expected_count}). "
                f"Edges with different sources but same FQN pair were incorrectly "
                f"merged into one."
            )
        else:
            # Double-check sources survive un-merged
            sources = [edge.source for edge in result]
            if set(sources) == {"source_A", "source_B"}:
                print(f"NOT CONFIRMED — got {actual_count} edges, both sources preserved")
            else:
                print(
                    f"CONFIRMED — got {actual_count} edges but sources are "
                    f"{sources}, not the expected distinct sources"
                )
    finally:
        os.unlink(tmp_path)

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
```

### Probe Output

```
CONFIRMED — got 1 edges (expected 2). Edges with different sources but same FQN pair were incorrectly merged into one.
```
