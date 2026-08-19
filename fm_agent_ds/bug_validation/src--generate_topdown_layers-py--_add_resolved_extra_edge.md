# Bug Report: _add_resolved_extra_edge

**Source file:** `fm_agent/extracted_functions/src/generate_topdown_layers-py/_add_resolved_extra_edge.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

The function registers a directed supplemental call edge from caller_fqn to callee_fqn. When caller_fqn equals callee_fqn (self-edge): no map is mutated, returns False. Otherwise, after the call: (1) all_callees_map[caller_fqn] contains callee_fqn  the edge is recorded in the complete callee set regardless of phase membership; (2) edge_aliases_map[callee_fqn][caller_fqn] contains every string from edge.info_names  the edge's alias names are recorded unconditionally; (3) when callee_fqn is a member of phase_fqns: callees_map[caller_fqn] contains callee_fqn AND callers_map[callee_fqn] contains caller_fqn  the edge is recorded in the phase-scoped forward and reverse maps; (4) when callee_fqn is NOT a member of phase_fqns: callees_map and callers_map are unchanged for this edge. Returns True when callee_fqn was absent from all_callees_map[caller_fqn] prior to the call (a new edge was registered); returns False when callee_fqn was already present. No element of any map is removed by this function.

---

### Actual Behavior

After execution, one of the following holds: (1) If caller_fqn equals edge.callee_fqn, no mutation occurs and the function returns False. (2) If caller_fqn is not equal to edge.callee_fqn, then: (a) all_callees_map[caller_fqn] is mutated to include edge.callee_fqn, i.e., all_callees_map[caller_fqn] = old(all_callees_map[caller_fqn])  {edge.callee_fqn}. (b) edge_aliases_map[edge.callee_fqn][caller_fqn] is mutated to include every string from edge.info_names, i.e., edge_aliases_map[edge.callee_fqn][caller_fqn] = old(edge_aliases_map[edge.callee_fqn][caller_fqn])  set(edge.info_names). (c) If edge.callee_fqn  phase_fqns, then an attempt is made to add edge.callee_fqn to callees_map[caller_fqn] and caller_fqn to callers_map[edge.callee_fqn]. If both keys exist (caller_fqn in callees_map and edge.callee_fqn in callers_map), the sets are updated: callees_map[caller_fqn] = old(callees_map[caller_fqn])  {edge.callee_fqn} and callers_map[edge.callee_fqn] = old(callers_map[edge.callee_fqn])  {caller_fqn}, and the function returns True iff edge.callee_fqn was not present in old(all_callees_map[caller_fqn]), i.e., old(|all_callees_map[caller_fqn]|)  old(|all_callees_map[caller_fqn]|) + 1. If either key is missing, a KeyError is raised after the mutations in steps 2a and 2b, and callees_map and callers_map remain unchanged. (d) If edge.callee_fqn  phase_fqns, callees_map and callers_map are unchanged, and the function returns True iff edge.callee_fqn was not present in old(all_callees_map[caller_fqn]), else False. No other mutable state is altered.

---

## Code Evidence

Line 17: if callee_fqn in phase_fqns:
Line 18:     callees_map[caller_fqn].add(callee_fqn)
Line 19:     callers_map[callee_fqn].add(caller_fqn)

---

## Trigger Condition

The specification requires that when callee_fqn is in phase_fqns, callees_map[caller_fqn] and callers_map[callee_fqn] are updated. The code does not guarantee those keys exist before calling .add(), causing a KeyError. This exception leaves all_callees_map and edge_aliases_map mutated but fails to perform the required phase-scoped mappings and does not return a boolean, violating the specification.

---

## How to trigger the bug

### Inputs

| Parameter | Value |
|-----------|-------|
| caller_fqn | `"caller::func"` |
| edge.callee_fqn | `"target::func"` |
| edge.info_names | `("alias1", "alias2")` |
| phase_fqns | `{"target::func", "other::func"}` |
| callees_map | `defaultdict(set)` (actual usage) |
| callers_map | `defaultdict(set)` (actual usage) |

### Expected (spec-correct) Output

`callees_map["caller::func"]` contains `"target::func"`, `callers_map["target::func"]` contains `"caller::func"`.

### Actual (buggy) Output

With `defaultdict(set)` (the actual calling pattern from `_build_call_graph` lines 310-311): the output **matches the spec exactly**. `callees_map["caller::func"]` contains `"target::func"` and `callers_map["target::func"]` contains `"caller::func"`. No KeyError occurs.

The KeyError claim only manifests if plain `dict` objects are passed instead of `defaultdict`. However, `_add_resolved_extra_edge` is a **private** function (name prefixed with `_`), called exclusively from `_build_call_graph` (lines 362-370, 372-381), which always initializes `callees_map` and `callers_map` as `defaultdict(set)` (lines 310-311). Therefore, the KeyError **cannot occur in real execution**.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. The bug does NOT reproduce with `defaultdict(set)` (actual usage). To see the KeyError vulnerability in isolation, pass plain `dict` objects:
3. Run the following snippet:

```python
from collections import defaultdict
from src.generate_topdown_layers import _add_resolved_extra_edge, _ResolvedExtraEdge

# With defaultdict(set) — actual usage, NO bug:
callees_map = defaultdict(set)
callers_map = defaultdict(set)
all_callees_map = defaultdict(set)
edge_aliases_map = defaultdict(lambda: defaultdict(set))

edge = _ResolvedExtraEdge(callee_fqn="target::func", info_names=("alias1",), source="test")
_add_resolved_extra_edge("caller::func", edge, {"target::func"},
                         callees_map, callers_map, all_callees_map, edge_aliases_map)
# >>> True, all maps correctly updated — spec satisfied.

# With plain dict without keys — KeyError (hypothetical):
callees_map = {}
callers_map = {}
# >>> KeyError: 'caller::func' — but this never happens in practice.
// actual (buggy) output: KeyError only with plain dict (never used in practice)
// expected (correct) output: maps correctly updated with defaultdict (always used)
```

---

## Probe Script

```python
"""Probe for bug: _add_resolved_extra_edge KeyError on callees_map/callers_map access.

Bug claim: Lines 463-464 (callees_map[caller_fqn].add(callee_fqn) and
callers_map[callee_fqn].add(caller_fqn)) raise KeyError when keys don't exist.

Verification: In the actual caller (_build_call_graph, lines 310-311),
callees_map and callers_map are always defaultdict(set), so the keys auto-create.
The function is private (_ prefix), only called from one place, always with
defaultdicts. The bug *cannot* manifest in real execution.
"""

import sys
import os
from collections import defaultdict

# Add repo root to sys.path so 'src' imports resolve
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from src.generate_topdown_layers import _add_resolved_extra_edge, _ResolvedExtraEdge


def test_with_defaultdict():
    """Test with defaultdict(set) — the actual usage pattern in _build_call_graph."""
    callees_map = defaultdict(set)
    callers_map = defaultdict(set)
    all_callees_map = defaultdict(set)
    edge_aliases_map = defaultdict(lambda: defaultdict(set))

    edge = _ResolvedExtraEdge(
        callee_fqn="target::func",
        info_names=("alias1", "alias2"),
        source="test",
    )
    phase_fqns = {"target::func", "other::func"}

    result = _add_resolved_extra_edge(
        caller_fqn="caller::func",
        edge=edge,
        phase_fqns=phase_fqns,
        callees_map=callees_map,
        callers_map=callers_map,
        all_callees_map=all_callees_map,
        edge_aliases_map=edge_aliases_map,
    )

    spec_satisfied = all([
        "target::func" in all_callees_map["caller::func"],
        "caller::func" in edge_aliases_map["target::func"],
        "target::func" in callees_map["caller::func"],
        "caller::func" in callers_map["target::func"],
        result is True,  # first time adding callee
    ])

    return spec_satisfied


def test_with_plain_dict():
    """Test with plain dict without required keys — the trigger condition."""
    callees_map = {}
    callers_map = {}
    all_callees_map = {"caller::func": set()}
    edge_aliases_map = {"target::func": {"caller::func": set()}}

    edge = _ResolvedExtraEdge(
        callee_fqn="target::func",
        info_names=("alias1",),
        source="test",
    )
    phase_fqns = {"target::func"}

    try:
        _add_resolved_extra_edge(
            caller_fqn="caller::func",
            edge=edge,
            phase_fqns=phase_fqns,
            callees_map=callees_map,
            callers_map=callers_map,
            all_callees_map=all_callees_map,
            edge_aliases_map=edge_aliases_map,
        )
        return False  # should have raised
    except KeyError as e:
        return True  # KeyError confirmed
    except Exception:
        return False


def main():
    errors = []

    try:
        defaultdict_ok = test_with_defaultdict()
    except Exception as e:
        defaultdict_ok = False
        errors.append(f"defaultdict test crashed: {e}")

    try:
        plain_dict_raises = test_with_plain_dict()
    except Exception as e:
        plain_dict_raises = False
        errors.append(f"plain dict test crashed: {e}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    # The bug is NOT CONFIRMED because the actual caller always uses
    # defaultdict(set), so the KeyError never occurs in real execution.
    # The plain_dict test shows the vulnerability exists in isolation,
    # but the function is private and its only call site guarantees
    # defaultdict arguments.
    if defaultdict_ok and plain_dict_raises:
        print(
            "NOT CONFIRMED — "
            "With defaultdict(set) (actual usage): spec IS satisfied, no KeyError. "
            "With plain dict (isolation): KeyError occurs. "
            "But the function is private and the sole caller provides defaultdict(set), "
            "so the bug does NOT manifest in practice."
        )
    elif defaultdict_ok and not plain_dict_raises:
        print("NOT CONFIRMED — defaultdict test passed, plain dict did not raise KeyError unexpectedly.")
    else:
        print("NOT CONFIRMED — unexpected behavior in tests.")


if __name__ == "__main__":
    main()
```

### Probe Output

```
NOT CONFIRMED — With defaultdict(set) (actual usage): spec IS satisfied, no KeyError. With plain dict (isolation): KeyError occurs. But the function is private and the sole caller provides defaultdict(set), so the bug does NOT manifest in practice.
```
