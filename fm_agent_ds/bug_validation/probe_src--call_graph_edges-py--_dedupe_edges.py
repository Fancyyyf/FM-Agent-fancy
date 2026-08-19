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

    # ---------- phase: construct edges whose first-occurrence order != sorted order ----------
    #
    # Input order (first occurrence):
    #   1. (B::func → B::callee)   Note: edge is fine without evidence, but fqn
    #   2. (A::func → A::callee)   and info_names are set to distinguish later.
    #   3. (C::func → A::callee)
    #   4. (B::func → B::callee)  [duplicate of #1 — should be merged]
    #
    # Sorted-by-key order (lexicographic by (caller.fqn, callee.fqn)):
    #   ("A::func", "A::callee"), ("B::func", "B::callee"), ("C::func", "A::callee")
    #
    # Specification-expected order (first-occurrence, deduplicated):
    #   ("B::func", "B::callee"), ("A::func", "A::callee"), ("C::func", "A::callee")

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
            # duplicate of edge 1 — exercises the union-of-names path
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

        # ---------- phase: call through the public API ----------
        result = load_call_edges(edge_file)

        # ---------- phase: inspect ----------
        actual_order = [(e.caller.fqn, e.callee.fqn) for e in result]

        # Specification-expected (first-occurrence order preserved)
        expected_spec = [
            ("B::func", "B::callee"),
            ("A::func", "A::callee"),
            ("C::func", "A::callee"),
        ]

        # Buggy-expected (sorted lexicographically)
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
