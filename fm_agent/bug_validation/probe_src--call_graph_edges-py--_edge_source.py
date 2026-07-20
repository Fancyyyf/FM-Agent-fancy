"""Probe script for _edge_source bug: evidence list filtering skips empty elements.

Bug: Line 168 filters out empty-after-stripping evidence elements.
For evidence=["", "a"], code returns "a", spec requires "; a".
"""
import json
import os
import sys
import tempfile

try:
    # Load via public package entry point
    from src.call_graph_edges import load_call_edges

    # Create a temporary JSON file with the trigger data
    edge_data = {
        "edges": [
            {
                "caller": {
                    "callsite_names": ["test_callsite"],
                },
                "callee": {
                    "fqn": "test::target_func",
                },
                "evidence": ["", "a"],
            }
        ]
    }

    # Write to temp file
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="probe_edge_source_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(edge_data, f)

        # Call the public API
        edges = load_call_edges(tmp_path)
    finally:
        os.unlink(tmp_path)

    if len(edges) != 1:
        print(f"ERROR: expected 1 edge, got {len(edges)}")
        sys.exit(1)

    actual = edges[0].source
    expected = "; a"

    # Bug confirmed if actual != expected
    passed = actual != expected

    if passed:
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — actual matched expected: {actual!r}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
