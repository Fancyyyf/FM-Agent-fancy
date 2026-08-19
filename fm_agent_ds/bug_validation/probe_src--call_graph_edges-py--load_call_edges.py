import sys
import tempfile
import json
import os
from pathlib import Path

try:
    # Add the repo root (two dirs up from this probe script) to sys.path
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, repo_root)
    from src.call_graph_edges import load_call_edges
except Exception as e:
    print(f'ERROR: Failed to import load_call_edges: {e}')
    sys.exit(1)

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)

    # Create two JSON edge files with names designed to expose ordering differences.
    # Both files contain edges with the SAME (caller.fqn, callee.fqn) key so that
    # _dedupe_edges merges them and the first-processed file "wins" for the source field.
    # The source string encodes which file it came from, making the winner observable.

    edge_z = {
        "edges": [{
            "caller": {"fqn": "same::caller", "callsite_names": ["from_z"]},
            "callee": {"fqn": "same::callee"},
            "source": "SOURCE_FROM_z"
        }]
    }
    edge_a = {
        "edges": [{
            "caller": {"fqn": "same::caller", "callsite_names": ["from_a"]},
            "callee": {"fqn": "same::callee"},
            "source": "SOURCE_FROM_a"
        }]
    }

    (tmp / "z.json").write_text(json.dumps(edge_z))
    (tmp / "a.json").write_text(json.dumps(edge_a))

    # Determine the natural rglob walk order (filesystem-dependent)
    rglob_files = [p.name for p in tmp.rglob("*") if p.is_file()]
    sorted_files = sorted(rglob_files)

    print(f"rglob walk order:   {rglob_files}")
    print(f"sorted(rglob) order: {sorted_files}")

    # Call load_call_edges
    result = load_call_edges(str(tmpdir))
    if not result:
        print("ERROR: load_call_edges returned empty list")
        sys.exit(1)

    merged_edge = result[0]
    actual_source = merged_edge.source
    print(f"load_call_edges merged edge source: {actual_source!r}")

    # The spec requires results in "filesystem walk order" (rglob order).
    # If rglob processes z.json first, the spec-consistent source would be "SOURCE_FROM_z".
    # If rglob processes a.json first, the spec-consistent source would be "SOURCE_FROM_a".
    # The current code uses sorted(rglob("*")), which always processes a.json before z.json
    # (alphabetical order), so the buggy output would have source "SOURCE_FROM_a"
    # regardless of the filesystem walk order.

    # Determine expected from spec (walk order)
    first_rglob_file = rglob_files[0]
    expected_from_walk = f"SOURCE_FROM_{first_rglob_file[0]}"  # "SOURCE_FROM_z" or "SOURCE_FROM_a"

    # Determine expected from sorted (buggy behavior)
    first_sorted_file = sorted_files[0]
    expected_from_sorted = f"SOURCE_FROM_{first_sorted_file[0]}"  # always "SOURCE_FROM_a"

    # If walk order and sorted order differ, we can confirm the bug:
    # The buggy code uses sorted order, NOT walk order.
    if rglob_files != sorted_files:
        # Order differs between walk and sort — we can check which one wins
        if actual_source == expected_from_sorted:
            print(f"CONFIRMED — load_call_edges uses sorted order (source={actual_source!r}) "
                  f"instead of walk order (expected={expected_from_walk!r})")
        elif actual_source == expected_from_walk:
            print(f"NOT CONFIRMED — load_call_edges correctly uses walk order "
                  f"(source={actual_source!r})")
        else:
            print(f"NOT CONFIRMED — unexpected source value: {actual_source!r}")
    else:
        # Walk order happens to equal sorted order on this filesystem
        if actual_source == expected_from_sorted:
            print(f"NOT CONFIRMED — on this filesystem, rglob walk order "
                  f"({rglob_files}) equals sorted order "
                  f"({sorted_files}); cannot distinguish buggy from correct behavior")
        else:
            print(f"NOT CONFIRMED — unexpected source value: {actual_source!r}")
