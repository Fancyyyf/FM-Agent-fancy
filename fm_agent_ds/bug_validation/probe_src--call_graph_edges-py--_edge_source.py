"""Probe for _edge_source bug: non-string evidence list entries are converted
via str(), treating integers etc. as valid provenance. The specification
requires evidence list entries to be strings — non-string entries should
result in the fallback being returned instead."""

import json
import os
import shutil
import sys
import tempfile

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.call_graph_edges import load_call_edges

    # Build an edge item where 'evidence' is a list of integers (non-strings).
    # The spec says evidence list entries are strings, so non-string entries
    # should be treated as no provenance → fallback should be returned.
    # The buggy code converts them with str(), producing e.g. "1; 2; 3".
    edges_data = {
        "edges": [
            {
                "caller": {"fqn": "A::func"},
                "callee": {"fqn": "B::callee"},
                "evidence": [1, 2, 3],
            }
        ]
    }

    tmpdir = tempfile.mkdtemp(prefix="bug_edge_source_")
    edge_file = os.path.join(tmpdir, "edges.json")
    try:
        with open(edge_file, "w") as f:
            json.dump(edges_data, f)

        result = load_call_edges(edge_file)

        actual_source = result[0].source

        # The fallback passed by the caller (_edge_from_mapping) is the
        # item_source string like "<filepath>:edges[1]". Since the evidence
        # entries are integers (not strings), the spec says they are not
        # valid provenance → fallback should be returned.
        # The buggy code uses str(), so actual_source would be "1; 2; 3".

        # The fallback always ends with the item source pattern.
        is_fallback = actual_source.endswith(f":edges[1]")

        if not is_fallback:
            print(
                f"CONFIRMED — actual (str-converted evidence): {actual_source!r} "
                f"| expected (fallback, evidence entries are not strings): "
                f"should end with :edges[1]"
            )
        else:
            print(
                f"NOT CONFIRMED — actual matched spec (fallback returned for non-string evidence): "
                f"{actual_source!r}"
            )

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

except Exception:
    import traceback

    traceback.print_exc()
    print("ERROR: probe script failed with an unhandled exception")
    sys.exit(1)
