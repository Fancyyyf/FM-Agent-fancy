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
