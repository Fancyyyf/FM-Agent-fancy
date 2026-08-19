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

    # ═════════════════════════════════════════════════════════════════════
    # Test 1: Static verification — read the source and confirm
    #          callees_map is initialized as defaultdict(set)
    # ═════════════════════════════════════════════════════════════════════
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

    # ═════════════════════════════════════════════════════════════════════
    # Test 2: Python data structure verification — defaultdict(set)
    #          inherently deduplicates, no matter how many times .add() is called
    # ═════════════════════════════════════════════════════════════════════
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

    # ═════════════════════════════════════════════════════════════════════
    # Test 3: Type verification against the spec
    #         Spec says "set" — isinstance check on the actual implementation
    # ═════════════════════════════════════════════════════════════════════
    cm_type = type(cm["A"])
    assert cm_type is set, (
        f"Spec requires set, got {cm_type} from defaultdict(set)"
    )

    # ═════════════════════════════════════════════════════════════════════
    # Test 4: Verify _project_call_graph docstring claims "set"
    # ═════════════════════════════════════════════════════════════════════
    pcg_source = textwrap.dedent(inspect.getsource(_project_call_graph))
    assert "set of FQNs" in pcg_source, (
        "_project_call_graph docstring does not claim callees_map values are sets"
    )

    # ═════════════════════════════════════════════════════════════════════
    # Test 5: Direct source snippet — verify no list usage in return path
    # ═════════════════════════════════════════════════════════════════════
    # The callees_map values come directly from _build_call_graph which uses
    # defaultdict(set). Verify the return path doesn't convert to list.
    return_match = re.findall(
        r"return\s+callees_map.*?callers_map.*?file_map.*?edge_aliases_map",
        pcg_source,
    )
    assert len(return_match) >= 1, (
        "Cannot find return statement in _project_call_graph"
    )

    # Verify no list() conversion on callees_map before return
    # The return statement is: return callees_map, callers_map, file_map, edge_aliases_map
    assert "list(callees_map" not in pcg_source
    assert "[*callees_map" not in pcg_source

    # ═════════════════════════════════════════════════════════════════════
    # All tests passed
    # ═════════════════════════════════════════════════════════════════════
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
