"""Probe script for _parse_callee bug: non-list info_names raises ValueError
but spec does not list this as an error condition.

Bug: Line 157 passes value.get("info_names", []) to _string_list(), which
raises ValueError when info_names is not a list. Per spec, a dict with a
well-formed fqn should return a CalleeTarget regardless of info_names type.
"""
import json
import os
import sys
import tempfile

try:
    from src.call_graph_edges import load_call_edges

    # Trigger: valid fqn, but info_names is a string instead of a list
    edge_data = {
        "edges": [
            {
                "caller": {
                    "callsite_names": ["test_callsite"],
                },
                "callee": {
                    "fqn": "test::target_func",
                    "info_names": "not_a_list_but_a_string",
                },
            }
        ]
    }

    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="probe_parse_callee_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(edge_data, f)

        edges = load_call_edges(tmp_path)
    finally:
        os.unlink(tmp_path)

    # Per spec, with a well-formed fqn, _parse_callee should return a CalleeTarget
    # (spec does not list non-list info_names as an error condition).
    # If we get here without an error, the bug is NOT confirmed.
    actual = "Returned gracefully (no error)"
    expected = "ValueError raised (spec violation)"
    print(f"NOT CONFIRMED — load_call_edges succeeded: {len(edges)} edge(s) loaded")

except ValueError as e:
    msg = str(e)
    if "callee.info_names" in msg and "string array" in msg:
        actual = f"ValueError: {msg}"
        expected = "CalleeTarget returned (spec says well-formed fqn suffices)"
        print(f"CONFIRMED — actual: {actual!r} | expected: {expected!r}")
    else:
        print(f"NOT CONFIRMED — ValueError raised but not about info_names: {msg}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
