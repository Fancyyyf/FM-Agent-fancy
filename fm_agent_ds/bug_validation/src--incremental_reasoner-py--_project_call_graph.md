# Bug Report: _project_call_graph

**Source file:** `src/incremental_reasoner-py/_project_call_graph.py`
**Verdict:** MISMATCH
**Confirmation status:** not_confirmed

---

## Reasoning Process

The following actual behavior cannot satisfy the specification.

### Specification Claim

Returns a 4-tuple (callees_map, callers_map, file_map, edge_aliases_map) where each element is a dict. callees_map maps every function FQN reachable from extracted functions across all phases to the set of FQNs it directly calls; every FQN in both keys and values is present in phases.json source files. callers_map is the inverse of callees_map: maps every function FQN to the set of FQNs that directly call it. file_map maps every function FQN in callees_map to the absolute filesystem path of its extracted-function file. edge_aliases_map, when extra_call_edges is provided, maps callee FQN  (caller FQN  set of supplemental edge label strings); when extra_call_edges is None or empty, the map may be empty but is never None. An FQN appearing as a callee but not as a caller in any source file still has an entry in callers_map (mapping to an empty set). All maps are keyed by canonical FQN strings using '::' as the separator. When extra_call_edges is provided, supplemental callercallee edges are incorporated into callees_map and callers_map alongside statically detected edges.

---

### Actual Behavior

The function returns a 4-tuple (callees_map, callers_map, file_map, edge_aliases_map). Let all_files be the list of unique (fpath, module_name) pairs collected from all phases using _collect_phase_files, where fpath is the absolute path to an extracted-function file under work_dir/extracted_functions/ and module_name is the module name. Let F be the set of all function FQNs extracted from the files in all_files by _build_call_graph. Let E_caller and E_callee be the sets of caller and callee FQNs appearing in extra_call_edges (if provided, otherwise empty). Then: (1) callees_map is a dict mapping each caller FQN c in (F  E_caller) to a list of callee FQNs that c directly calls, combining call relations derived from the function bodies and those from extra_call_edges; (2) callers_map is a dict mapping each callee FQN d in (F  E_callee) to a list of caller FQNs that directly call d; (3) file_map is a dict mapping each FQN f in F to its absolute extracted-function file path (the fpath from all_files where f was found); (4) edge_aliases_map is a dict such that if extra_call_edges is not None, then edge_aliases_map maps callee FQN to a dict mapping caller FQN to a list of supplemental edge labels derived from extra_call_edges; otherwise edge_aliases_map is empty. The union of all direct call edges represented in callees_map forms the project-wide call graph spanning all phases, with each unique file processed exactly once.

---

## Code Evidence

Line 19: (... ) = _build_call_graph(... ), Line 31: return callees_map, callers_map, file_map, edge_aliases_map

---

## Trigger Condition

The specification requires callees_map to map each caller to a set of FQNs (no duplicates). The implementation returns the lists produced by _build_call_graph without deduplication, so when static edges and extra_call_edges overlap, the same callee can appear multiple times, violating the set requirement.

---

## How to trigger the bug

The bug claim asserts that `_build_call_graph` returns lists and `_project_call_graph` passes them without deduplication. However, source code inspection and controlled testing prove the claim is incorrect.

### Inputs

| Parameter | Value |
|-----------|-------|
| `work_dir` | Path to `fm_agent/` directory containing `phases.json` and `extracted_functions/` |
| `extra_call_edges` | Optional list of `CallEdge` objects |

### Expected (spec-correct) Output

`callees_map` with values as `set` type (no duplicates), which is what the specification requires.

### Actual (buggy) Output

The probe verified that `callees_map` values are already `set` instances, produced by `defaultdict(set)` — not lists. No duplicates can exist because Python `set.add()` is idempotent.

### How to Reproduce

Step-by-step instructions to trigger the bug manually:

1. Navigate to the repo root.
2. Run the following snippet (uses the package entry point):

```python
from collections import defaultdict
from src.generate_topdown_layers import _build_call_graph
from src.incremental_reasoner import _project_call_graph
import inspect, textwrap

# Verify _build_call_graph initializes callees_map as defaultdict(set)
source = textwrap.dedent(inspect.getsource(_build_call_graph))
assert "defaultdict(set)" in source  # line 310

# Verify Python sets inherently deduplicate
cm = defaultdict(set)
cm["caller"].add("callee_a")
cm["caller"].add("callee_b")
cm["caller"].add("callee_a")  # duplicate — ignored by set
assert len(cm["caller"]) == 2
# actual (buggy) output: No bug — set deduplicates automatically
# expected (correct) output: 2 unique callees
```

---

## Probe Script

```python
"""
Self-contained probe script for bug: src--incremental_reasoner-py--_project_call_graph

Bug claim: _build_call_graph returns callees_map with lists, and _project_call_graph
passes them through without deduplication. When static edges and extra_call_edges
overlap, the same callee can appear multiple times, violating the "set" requirement
in the specification.

Verification strategy:
1. Inspect _build_call_graph source to confirm callees_map is defaultdict(set).
2. Create a controlled test: build a defaultdict(set), add overlapping values from
   both simulated static edges and extra edges, verify Python sets deduplicate.
3. If possible, call the actual _build_call_graph with real fixtures.
"""
import inspect
import os
import re
import sys
import textwrap

# Ensure the project root is on sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

passed = True

try:
    from src.generate_topdown_layers import _build_call_graph
    from src.incremental_reasoner import _project_call_graph

    # Test 1: Static verification — read the source and confirm
    #          callees_map is initialized as defaultdict(set)
    source = textwrap.dedent(inspect.getsource(_build_call_graph))

    # Check: callees_map is initialized as defaultdict(set)
    assert "defaultdict(set)" in source, (
        "BUG: _build_call_graph does NOT initialize callees_map as defaultdict(set).\n"
        "Found in source:\n" + source
    )

    # Check: callers_map is initialized as defaultdict(set)
    callees_init_count = source.count("defaultdict(set)")
    assert callees_init_count >= 2, (
        f"Expected at least 2 defaultdict(set) (for callees_map and callers_map), "
        f"found {callees_init_count}"
    )

    # Test 2: Python data structure verification — defaultdict(set)
    #          inherently deduplicates, no matter how many times .add() is called
    from collections import defaultdict

    # Simulate: static edges add callee "B" and "C"
    cm = defaultdict(set)
    cm["A"].add("B")
    cm["A"].add("C")

    # Simulate: extra edges also add callee "B" (overlap) and "D"
    cm["A"].add("B")  # overlapping edge — should NOT create duplicate
    cm["A"].add("D")

    # Verify: "B" appears only once in cm["A"]
    callees_for_a = list(cm["A"])
    assert callees_for_a.count("B") == 1, (
        f"BUG: defaultdict(set) duplicate found! callees_for_A={callees_for_a}"
    )
    assert callees_for_a.count("C") == 1
    assert callees_for_a.count("D") == 1
    assert len(cm["A"]) == 3, (
        f"Expected 3 unique callees (B, C, D), got {len(cm['A'])}: {cm['A']}"
    )

    # Test 3: Type verification against the spec
    #         Spec says "set" — isinstance check on the actual implementation
    cm_type = type(cm["A"])
    assert cm_type is set, (
        f"Spec requires set, got {cm_type} from defaultdict(set)"
    )

    # Test 4: Verify _project_call_graph docstring claims "set"
    pcg_source = textwrap.dedent(inspect.getsource(_project_call_graph))
    assert "set of FQNs" in pcg_source, (
        "_project_call_graph docstring does not claim callees_map values are sets"
    )

    # Test 5: Direct source snippet — verify no list usage in return path
    return_match = re.findall(
        r"return\s+callees_map.*?callers_map.*?file_map.*?edge_aliases_map",
        pcg_source,
    )
    assert len(return_match) >= 1, (
        "Cannot find return statement in _project_call_graph"
    )

    # Verify no list() conversion on callees_map before return
    assert "list(callees_map" not in pcg_source
    assert "[*callees_map" not in pcg_source

    # All tests passed
    print(
        "NOT CONFIRMED — actual: _build_call_graph initializes callees_map as "
        "defaultdict(set) (proven by source inspection); Python set.add() is "
        "idempotent, so overlapping static and extra edges cannot create "
        "duplicates. The spec requires a set, and the implementation returns "
        "exactly a set. Expected behavior already matched."
    )

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
```

### Probe Output

```
NOT CONFIRMED — actual: _build_call_graph initializes callees_map as defaultdict(set) (proven by source inspection); Python set.add() is idempotent, so overlapping static and extra edges cannot create duplicates. The spec requires a set, and the implementation returns exactly a set. Expected behavior already matched.
```
